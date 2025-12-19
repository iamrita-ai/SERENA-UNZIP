import datetime
from typing import Dict, Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from config import Config


# ----------------------------------------------------
#  Config / Mode detection
# ----------------------------------------------------

MONGO_URI = Config.MONGO_URI

# Agar MONGO_URI empty hai ya localhost hai -> Render pe likely kaam nahi karega
USE_DB = bool(MONGO_URI) and ("localhost" not in MONGO_URI and "127.0.0.1" not in MONGO_URI)

if USE_DB:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[Config.DB_NAME]
    users_col = db["users"]
    files_col = db["temp_files"]
else:
    client = None
    users_col = None
    files_col = None

# In‑memory fallback (jab DB use nahi ho raha ho ya fail ho jaye)
_mem_users: Dict[int, Dict[str, Any]] = {}
_mem_files: Dict[str, Dict[str, Any]] = {}


def _default_user(user_id: int) -> Dict[str, Any]:
    today = datetime.date.today().isoformat()
    return {
        "_id": user_id,
        "is_premium": False,
        "is_banned": False,
        "settings": {
            "auto_delete_min": Config.AUTO_DELETE_DEFAULT_MIN,
            "lang": "en",
            "default_extract_mode": "full",  # full/single
            "preferred_output": "file",     # file/link
        },
        "stats": {
            "last_reset": today,
            "daily_tasks": 0,
            "daily_size_mb": 0.0,
            "last_task_ts": None,
        },
    }


async def _safe_db(coro, default=None):
    """DB operation ko safe bana deta hai; agar error aaya to default return karega."""
    if not USE_DB:
        return default
    try:
        return await coro
    except PyMongoError:
        return default
    except Exception:
        return default


# ----------------------------------------------------
#  User helpers
# ----------------------------------------------------

async def get_or_create_user(user_id: int) -> Dict[str, Any]:
    today = datetime.date.today().isoformat()

    # In‑memory first
    user = _mem_users.get(user_id)

    # DB se fetch karne ki koshish (agar enabled ho)
    if USE_DB and user is None:
        doc = await _safe_db(users_col.find_one({"_id": user_id}))
        if doc:
            user = doc

    if user is None:
        user = _default_user(user_id)
        _mem_users[user_id] = user
        if USE_DB:
            await _safe_db(users_col.insert_one(dict(user)))
    else:
        # daily reset check
        stats = user.get("stats", {})
        if stats.get("last_reset") != today:
            stats["last_reset"] = today
            stats["daily_tasks"] = 0
            stats["daily_size_mb"] = 0.0
            user["stats"] = stats
            _mem_users[user_id] = user
            if USE_DB:
                await _safe_db(
                    users_col.update_one(
                        {"_id": user_id},
                        {
                            "$set": {
                                "stats.last_reset": today,
                                "stats.daily_tasks": 0,
                                "stats.daily_size_mb": 0.0,
                            }
                        },
                    )
                )

    return user


async def update_user_stats(user_id: int, size_mb: float):
    # in‑memory
    user = _mem_users.get(user_id)
    if not user:
        user = await get_or_create_user(user_id)

    stats = user.setdefault("stats", {})
    stats["daily_tasks"] = stats.get("daily_tasks", 0) + 1
    stats["daily_size_mb"] = float(stats.get("daily_size_mb", 0.0)) + float(size_mb)
    stats["last_task_ts"] = datetime.datetime.utcnow()
    _mem_users[user_id] = user

    if USE_DB:
        await _safe_db(
            users_col.update_one(
                {"_id": user_id},
                {
                    "$inc": {
                        "stats.daily_tasks": 1,
                        "stats.daily_size_mb": float(size_mb),
                    },
                    "$set": {
                        "stats.last_task_ts": datetime.datetime.utcnow(),
                    },
                },
                upsert=True,
            )
        )


async def set_premium(user_id: int, value: bool = True):
    user = _mem_users.get(user_id) or _default_user(user_id)
    user["is_premium"] = value
    _mem_users[user_id] = user

    if USE_DB:
        await _safe_db(
            users_col.update_one(
                {"_id": user_id},
                {"$set": {"is_premium": value}},
                upsert=True,
            )
        )


async def set_ban(user_id: int, value: bool = True):
    user = _mem_users.get(user_id) or _default_user(user_id)
    user["is_banned"] = value
    _mem_users[user_id] = user

    if USE_DB:
        await _safe_db(
            users_col.update_one(
                {"_id": user_id},
                {"$set": {"is_banned": value}},
                upsert=True,
            )
        )


async def is_banned(user_id: int) -> bool:
    # memory first
    user = _mem_users.get(user_id)
    if user is not None:
        return bool(user.get("is_banned", False))

    if USE_DB:
        doc = await _safe_db(
            users_col.find_one({"_id": user_id}, {"is_banned": 1}),
            default=None,
        )
        if doc is not None:
            # cache in memory
            _mem_users[user_id] = doc
            return bool(doc.get("is_banned", False))

    return False


async def get_all_users():
    if USE_DB:
        users = []
        cursor = await _safe_db(users_col.find({}, {"_id": 1}))
        if cursor is not None:
            async for doc in cursor:
                users.append(doc["_id"])
            # warm memory
            for uid in users:
                _mem_users.setdefault(uid, _default_user(uid))
            return users

    # fallback to memory only
    return list(_mem_users.keys())


async def count_users():
    if USE_DB:
        total = await _safe_db(users_col.count_documents({}), default=0) or 0
        premium = await _safe_db(
            users_col.count_documents({"is_premium": True}), default=0
        ) or 0
        banned = await _safe_db(
            users_col.count_documents({"is_banned": True}), default=0
        ) or 0
        return total, premium, banned

    # memory only
    total = len(_mem_users)
    premium = sum(1 for u in _mem_users.values() if u.get("is_premium"))
    banned = sum(1 for u in _mem_users.values() if u.get("is_banned"))
    return total, premium, banned


# ----------------------------------------------------
#  Temp files helpers (for cleanup_worker)
# ----------------------------------------------------

async def register_temp_path(user_id: int, path: str, ttl_min: int):
    now = datetime.datetime.utcnow()

    # memory
    _mem_files[path] = {
        "user_id": user_id,
        "path": path,
        "created_at": now,
        "ttl_min": ttl_min,
    }

    # DB
    if USE_DB:
        await _safe_db(
            files_col.insert_one(
                {
                    "user_id": user_id,
                    "path": path,
                    "created_at": now,
                    "ttl_min": ttl_min,
                }
            )
        )


async def get_expired_temp_paths(
    now: Optional[datetime.datetime] = None,
):
    if now is None:
        now = datetime.datetime.utcnow()

    expired_paths = []

    # memory
    for p, info in list(_mem_files.items()):
        created = info["created_at"]
        ttl_min = info["ttl_min"]
        if created + datetime.timedelta(minutes=ttl_min) <= now:
            expired_paths.append(p)
            _mem_files.pop(p, None)

    # DB
    if USE_DB:
        # purana simple scan approach
        cursor = await _safe_db(files_col.find({}))
        remove_ids = []
        if cursor is not None:
            async for doc in cursor:
                created = doc.get("created_at")
                ttl_min = doc.get("ttl_min", Config.AUTO_DELETE_DEFAULT_MIN)
                if (
                    created
                    and created + datetime.timedelta(minutes=ttl_min) <= now
                ):
                    expired_paths.append(doc.get("path"))
                    remove_ids.append(doc["_id"])
        if remove_ids:
            await _safe_db(files_col.delete_many({"_id": {"$in": remove_ids}}))

    # unique paths only
    return list({p for p in expired_paths if p})
