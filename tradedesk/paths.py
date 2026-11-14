"""File locations. All user data lives in a 'data' folder next to the app
(to back everything up, just copy that folder)."""
import os
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # PyInstaller exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Where bundled read-only files (assets/) live: next to the sources, or inside the PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


ASSETS_DIR = resource_dir() / "assets"
DATA_DIR = app_dir() / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "tradedesk.db"
_OLD_DB_NAME = "trade" + "hub.db"          # database name used before 0.7.0 (renamed automatically)
SETTINGS_PATH = DATA_DIR / "settings.json"
CHECKLIST_TEMPLATE_PATH = DATA_DIR / "checklist_template.json"
CALENDAR_CACHE_PATH = DATA_DIR / "calendar_cache.json"
CALENDAR_NOTES_PATH = DATA_DIR / "calendar_notes.json"
ERROR_LOG_PATH = DATA_DIR / "error.log"


def migrate_old_db(data_dir: Path = None, new_path: Path = None) -> bool:
    """Before 0.7.0 the database had a different file name. Rename it once so existing trades are kept."""
    data_dir = data_dir or DATA_DIR
    new_path = new_path or DB_PATH
    old = data_dir / _OLD_DB_NAME
    if old.exists() and not new_path.exists():
        os.replace(old, new_path)
        return True
    return False


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        migrate_old_db()
    except OSError:
        pass


def atomic_write_text(path: Path, text: str) -> None:
    """Write to a temp file first and then replace, so a crash can never leave a half-written file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
