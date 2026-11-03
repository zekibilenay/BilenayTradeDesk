import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

BG = "#0f141b"
PANEL = "#151b25"
PANEL2 = "#1b2330"
BORDER = "#2a3342"
FG = "#e6e9ef"
MUTED = "#8b94a5"
ACCENT = "#3b82f6"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
ORANGE = "#f59e0b"
SELECT = "#1e3a5f"

VERDICT_COLORS = {"green": GREEN, "yellow": YELLOW, "red": RED, "none": MUTED, "": MUTED}

F = {"ui": "Segoe UI", "mono": "Consolas"}


def _pick(root, candidates, default):
    try:
        fams = set(tkfont.families(root))
    except Exception:
        return default
    for c in candidates:
        if c in fams:
            return c
    return default


def apply_theme(root: tk.Tk) -> None:
    F["ui"] = _pick(root, ["Segoe UI", "Helvetica Neue", "Ubuntu", "DejaVu Sans"], "TkDefaultFont")
    F["mono"] = _pick(root, ["Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"], "TkFixedFont")
    ui = F["ui"]

    root.configure(bg=BG)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL2, bordercolor=BORDER,
                lightcolor=BG, darkcolor=BG, troughcolor=PANEL, focuscolor=BG, font=(ui, 10))
    s.configure("TFrame", background=BG)
    s.configure("Panel.TFrame", background=PANEL)
    s.configure("TLabel", background=BG, foreground=FG)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("Title.TLabel", font=(ui, 13, "bold"))
    s.configure("TSeparator", background=BORDER)

    s.configure("TButton", background=PANEL2, foreground=FG, padding=(10, 5), borderwidth=1, relief="flat")
    s.map("TButton", background=[("active", "#26324a"), ("pressed", ACCENT)])
    s.configure("Accent.TButton", background=ACCENT, foreground="white")
    s.map("Accent.TButton", background=[("active", "#2563eb"), ("pressed", "#1d4ed8")])
    s.configure("Danger.TButton", background="#3a1f24", foreground="#fca5a5")
    s.map("Danger.TButton", background=[("active", "#5a2a31")])
    s.configure("Seg.TButton", background=PANEL2, foreground=MUTED, padding=(14, 5))
    s.configure("SegOn.TButton", background=ACCENT, foreground="white", padding=(14, 5))
    s.map("SegOn.TButton", background=[("active", "#2563eb")])

    s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(8, 8, 8, 0))
    s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(20, 9), font=(ui, 10, "bold"))
    s.map("TNotebook.Tab", background=[("selected", PANEL2)], foreground=[("selected", FG)])

    s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=26,
                borderwidth=0, font=(ui, 10))
    s.configure("Treeview.Heading", background=PANEL2, foreground=MUTED, relief="flat", font=(ui, 9, "bold"))
    s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", FG)])
    s.map("Treeview.Heading", background=[("active", PANEL2)])

    s.configure("TCheckbutton", background=BG, foreground=FG)
    s.map("TCheckbutton", background=[("active", BG)], indicatorcolor=[("selected", ACCENT)])
    s.configure("TEntry", fieldbackground=PANEL2, foreground=FG, insertcolor=FG, padding=4)
    s.configure("Invalid.TEntry", fieldbackground="#4a1f24", foreground=FG, insertcolor=FG, padding=4)
    s.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2, foreground=FG,
                arrowcolor=MUTED, padding=4, selectbackground=ACCENT, selectforeground="white")
    # readonly comboboxes must not show a highlighted (selected) text block after choosing a value
    s.map("TCombobox",
          fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", FG)],
          selectbackground=[("readonly", PANEL2)], selectforeground=[("readonly", FG)])
    s.configure("TSpinbox", fieldbackground=PANEL2, foreground=FG, arrowcolor=MUTED, padding=3)
    s.configure("Vertical.TScrollbar", background=PANEL2, troughcolor=PANEL, arrowcolor=MUTED,
                bordercolor=PANEL)
    s.configure("TPanedwindow", background=BG)

    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.font", (ui, 10))


def style_text(w: tk.Text, font=None) -> None:
    w.configure(bg=PANEL2, fg=FG, insertbackground=FG, selectbackground=ACCENT, selectforeground="white",
                relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                padx=8, pady=6, wrap="word", font=font or (F["ui"], 10), undo=True)
