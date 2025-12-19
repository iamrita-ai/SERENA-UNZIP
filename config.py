import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram API credentials (ENV preferred)
    API_ID = int(os.getenv("API_ID", "123456"))          # Render env
    API_HASH = os.getenv("API_HASH", "change_me")        # Render env
    BOT_TOKEN = os.getenv("BOT_TOKEN", "123:ABC")        # Render env

    # Mongo
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/serena_unzip")

    # Hard-coded IDs (as requested)
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003286415377"))
    FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "serenaunzipbot")
    OWNER_IDS = {6518065496, 1598576202}
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "technicalserena")

    # General
    BOT_NAME = "Serena Unzip"
    START_PIC = os.getenv("START_PIC", None)  # file_id ya http url

    TEMP_DIR = os.getenv("TEMP_DIR", "downloads")

    # Progress bar
    PROGRESS_UPDATE_INTERVAL = int(os.getenv("PROGRESS_UPDATE_INTERVAL", "5"))  # seconds

    # Cleanup & limits
    AUTO_DELETE_DEFAULT_MIN = int(os.getenv("AUTO_DELETE_DEFAULT_MIN", "30"))  # server files TTL
    FREE_DAILY_TASK_LIMIT = int(os.getenv("FREE_DAILY_TASK_LIMIT", "30"))
    FREE_DAILY_SIZE_MB = int(os.getenv("FREE_DAILY_SIZE_MB", "4096"))
    FREE_MIN_WAIT_SEC = int(os.getenv("FREE_MIN_WAIT_SEC", "300"))  # 5 min
    PREMIUM_MIN_WAIT_SEC = int(os.getenv("PREMIUM_MIN_WAIT_SEC", "10"))

    # File size caps (MB)
    MAX_ARCHIVE_SIZE_FREE_MB = int(os.getenv("MAX_ARCHIVE_SIZE_FREE_MB", "2048"))  # 2 GB
    MAX_ARCHIVE_SIZE_PREMIUM_MB = int(os.getenv("MAX_ARCHIVE_SIZE_PREMIUM_MB", "10240"))  # 10 GB+

    # Misc
    DB_NAME = os.getenv("DB_NAME", "serena_unzip")
