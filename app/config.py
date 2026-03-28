from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

APPID = os.getenv("BOT_APPID", "").strip()
APPSECRET = os.getenv("BOT_APPSECRET", "").strip()
USE_SANDBOX = os.getenv("BOT_USE_SANDBOX", "true").lower() == "true"
ADMIN_OPENID = os.getenv("ADMIN_OPENID", "").strip()

DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
INBOX_DIR = STORAGE_DIR / "inbox"
ARCHIVE_DIR = STORAGE_DIR / "archive"
TEMP_DIR = STORAGE_DIR / "temp"
EXPORT_DIR = BASE_DIR / "exports"
LOG_DIR = BASE_DIR / "logs"

for p in [DATA_DIR, STORAGE_DIR, INBOX_DIR, ARCHIVE_DIR, TEMP_DIR, EXPORT_DIR, LOG_DIR]:
    p.mkdir(parents=True, exist_ok=True)