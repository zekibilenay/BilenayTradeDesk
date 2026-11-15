"""File locations. All user data lives in a 'data' folder next to the app (to back everything up, just copy that
folder). Exception: the macOS app keeps it in ~/Library/Application Support/BilenayTradeDesk (see platform_utils)."""
import os
import sys
from pathlib import Path

from . import platform_utils


def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # PyInstaller exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Where bundled read-only files (assets/) live: next to the sources, or inside the PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _writable(folder: Path) -> bool:
    """Can the folder be created and written to? Checked by really writing a small file (os.access is not reliable
    on Windows). Folders that did not exist yet are removed again, so merely importing this module leaves no trace."""
    missing = []
    probe_dir = folder
    while not probe_dir.exists() and probe_dir != probe_dir.parent:
        missing.append(probe_dir)
        probe_dir = probe_dir.parent
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False
    finally:
        for d in missing:                                   # deepest first
            try:
                d.rmdir()
            except OSError:
                pass


ASSETS_DIR = resource_dir() / "assets"
DATA_DIR = platform_utils.choose_data_dir(app_dir(), getattr(sys, "frozen", False), sys.platform, Path.home(),
                                          os.environ, _writable)
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
