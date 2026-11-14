import sys
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import messagebox, ttk

from . import APP_NAME, APP_VERSION, theme
from .calendar_tab import CalendarTab
from .checklist_tab import ChecklistTab
from .db import Database
from .journal_tab import JournalTab
from .paths import ASSETS_DIR, DB_PATH, ERROR_LOG_PATH, SETTINGS_PATH, ensure_dirs
from .settings import Settings


class TradeDeskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.settings = Settings(SETTINGS_PATH)
        self.db = Database(DB_PATH)
        theme.set_theme(self.settings.get("theme"))
        theme.apply_theme(self)

        self.title(f"{APP_NAME} {APP_VERSION}")
        self._set_icon()
        self.geometry(self._safe_geometry(self.settings.get("geometry")))
        self.minsize(1100, 700)
        self._maximize()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.checklist = ChecklistTab(nb, self.db)
        self.calendar = CalendarTab(nb, self.settings)
        self.journal = JournalTab(nb, self.db)
        nb.add(self.checklist, text="Pre-Trade Checklist")
        nb.add(self.calendar, text="Economic Calendar")
        nb.add(self.journal, text="Trade Journal")
        self._build_theme_picker()

        # click on an empty spot -> the text cursor leaves whatever box it was in (and that box saves itself)
        self.bind_all("<Button-1>", self._clear_focus, add="+")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _maximize(self):
        """Start with the window filling the screen (the title bar stays, so it can still be restored)."""
        try:
            self.state("zoomed")                       # Windows / macOS
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)       # Linux
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ theme
    def _build_theme_picker(self):
        """Theme selector at the right end of the tab bar."""
        bar = ttk.Frame(self)
        ttk.Label(bar, text="Theme", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.theme_var = tk.StringVar(value=theme.current_name())
        box = ttk.Combobox(bar, textvariable=self.theme_var, values=theme.names(), state="readonly", width=12,
                           exportselection=False)
        box.pack(side="left")
        box.bind("<<ComboboxSelected>>", lambda e=None: (box.selection_clear(), self._on_theme(self.theme_var.get())))
        bar.place(relx=1.0, x=-14, y=13, anchor="ne")
        bar.lift()

    def _on_theme(self, name):
        """Switch the theme of the running window (nothing is rebuilt: scroll positions and text stay)."""
        if name == theme.current_name():
            return
        old = theme.palette()
        theme.set_theme(name)
        theme.apply_theme(self)
        theme.recolor(self, old, theme.palette())
        self.settings.set("theme", name)
        self.focus_set()

    _KEEP_FOCUS = ("Entry", "TEntry", "Text", "TCombobox", "TSpinbox", "Spinbox", "Listbox")

    def _clear_focus(self, event):
        w = event.widget
        try:
            if not isinstance(w, tk.Misc) or w.winfo_toplevel() is not self:
                return                                  # other windows (image viewer, combobox lists)
            if w.winfo_class() in self._KEEP_FOCUS:
                return                                  # clicking into an input keeps the cursor there
            self.focus_set()
        except (tk.TclError, KeyError):
            pass

    def _set_icon(self):
        """Title-bar / taskbar icon. (Until v0.2 only the .exe file had an icon; the window itself kept Tk's
        default feather.) Windows uses the .ico (all its sizes), other systems the .png."""
        ico, png = ASSETS_DIR / "icon.ico", ASSETS_DIR / "icon.png"
        if sys.platform.startswith("win") and ico.exists():
            try:
                self.iconbitmap(default=str(ico))      # also applies to every later Toplevel (image viewer)
                return
            except tk.TclError:
                pass
        if png.exists():
            try:
                self._icon_img = tk.PhotoImage(file=str(png))
                self.iconphoto(True, self._icon_img)
            except tk.TclError:
                pass

    @staticmethod
    def _safe_geometry(g):
        try:
            w, rest = str(g).split("x", 1)
            if int(w) >= 800:
                return str(g)
        except Exception:
            pass
        return "1500x900"

    def report_callback_exception(self, exc, val, tb):
        """In a windowed (console-less) exe errors would vanish: log them to data/error.log."""
        text = "".join(traceback.format_exception(exc, val, tb))
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n{text}")
        except OSError:
            pass
        messagebox.showerror(APP_NAME, f"An unexpected error occurred:\n\n{val}\n\n"
                                       f"Details were written to: {ERROR_LOG_PATH}")

    def _on_close(self):
        for tab in (self.checklist, self.calendar, self.journal):
            try:
                tab.save_current()
            except Exception:
                pass
        try:
            g = self.geometry().split("+")[0]
            self.settings.set("geometry", g)
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass
        self.destroy()

