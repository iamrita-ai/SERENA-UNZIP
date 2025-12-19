import asyncio
import os
import shutil

from database import get_expired_temp_paths
from config import Config


async def cleanup_worker():
    # periodic cleanup of temp paths
    while True:
        try:
            expired = await get_expired_temp_paths()
            for path in expired:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    elif os.path.isfile(path):
                        os.remove(path)
                except Exception:
                    pass
        except Exception:
            pass

        await asyncio.sleep(60)  # every minute
