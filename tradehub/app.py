import tkinter as tk
import traceback
from datetime import datetime
from tkinter import messagebox, ttk

from . import APP_NAME, APP_VERSION, theme
from .calendar_tab import CalendarTab
from .checklist_tab import ChecklistTab
from .db import Database
from .journal_tab import JournalTab
from .paths import DB_PATH, ERROR_LOG_PATH, SETTINGS_PATH, ensure_dirs
from .settings import Settings


class TradeHubApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.settings = Settings(SETTINGS_PATH)
        self.db = Database(DB_PATH)
        theme.apply_theme(self)

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry(self._safe_geometry(self.settings.get("geometry")))
        self.minsize(1100, 700)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.checklist = ChecklistTab(nb, self.db)
        self.calendar = CalendarTab(nb, self.settings)
        self.journal = JournalTab(nb, self.db)
        nb.add(self.checklist, text="Pre-Trade Checklist")
        nb.add(self.calendar, text="Economic Calendar")
        nb.add(self.journal, text="Trade Journal")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
