"""Everything that differs between Windows, macOS and Linux, kept free of tkinter so it can be unit-tested.

Used by: paths.py (where the data folder is), widgets.py (mouse wheel), journal_tab.py / calendar_tab.py
(shortcuts and the hints that mention them), app.py (Cmd+Q)."""
import sys
from pathlib import Path

APP_FOLDER = "BilenayTradeDesk"


def is_windows(platform=None):
    return (platform or sys.platform).startswith("win")


def is_mac(platform=None):
    return (platform or sys.platform) == "darwin"


# ---- data folder -----------------------------------------------------------------------------------------------

def user_data_dir(platform, home, env):
    """The per-user place for app data on each system."""
    home = Path(home)
    if is_mac(platform):
        return home / "Library" / "Application Support" / APP_FOLDER
    if is_windows(platform):
        return Path(env.get("APPDATA") or home / "AppData" / "Roaming") / APP_FOLDER
    return Path(env.get("XDG_DATA_HOME") or home / ".local" / "share") / APP_FOLDER


def choose_data_dir(app_dir, frozen, platform, home, env, writable):
    """Where the 'data' folder lives.

    - Running from source, or the Windows / Linux build: next to the app (portable, "back up = copy data/").
    - The macOS .app: a .app bundle must not hold data (it is replaced on every update and may be read-only), so
      the data goes to ~/Library/Application Support/BilenayTradeDesk.
    - If the chosen place can not be written to (an app copied into Program Files or /opt), the per-user folder is
      used instead, so the app starts instead of failing.
    `writable(path)` tells whether a folder can be created / written."""
    app_dir = Path(app_dir)
    if frozen and is_mac(platform):
        return user_data_dir(platform, home, env)
    beside = app_dir / "data"
    if writable(beside):
        return beside
    return user_data_dir(platform, home, env)


# ---- mouse wheel -------------------------------------------------------------------------------------------------

def wheel_notches(num, delta, platform=None):
    """One mouse-wheel event -> how many wheel 'notches' it is worth (positive = up).
    Windows: delta is a multiple of 120 (touchpads send fractions). Linux/X11 (Tk 8.6): buttons 4 / 5.
    macOS: delta is a small number of lines (1, 2, 3 ... faster when the wheel / trackpad accelerates)."""
    if num == 4:
        return 1.0
    if num == 5:
        return -1.0
    try:
        delta = float(delta)
    except (TypeError, ValueError):
        return 0.0
    if is_mac(platform):
        return delta / 4.0
    return delta / 120.0


# ---- shortcuts and the texts that name them ---------------------------------------------------------------------

def paste_shortcut(platform=None):
    return "⌘V" if is_mac(platform) else "Ctrl+V"


def screenshot_hint(platform=None):
    """How to put a screenshot on the clipboard on this system."""
    if is_windows(platform):
        return "Win+Shift+S"
    if is_mac(platform):
        return "Cmd+Ctrl+Shift+4"
    return "copy it to the clipboard"


def clipboard_help(platform=None):
    """Shown when the clipboard can not be read for images (Linux needs a small helper program for that)."""
    if is_mac(platform) or is_windows(platform):
        return ""
    return "pasting images needs xclip (X11) or wl-clipboard (Wayland) — install one, or use “Add file…”"
