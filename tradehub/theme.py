import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# --- palette (v0.3: deeper neutral background, brighter accents) -------------------------------------
BG = "#0d1117"
PANEL = "#151b24"
PANEL2 = "#1c2431"
PANEL3 = "#263044"          # hover / raised surfaces
BORDER = "#2a3548"
FG = "#e6edf3"
MUTED = "#8b98ab"
ACCENT = "#4c8dff"
ACCENT_DK = "#3a74e0"
ACCENT_BG = "#16294a"       # subtle accent-tinted surface (banners)
GREEN = "#34c77b"
YELLOW = "#e5b73b"
RED = "#f0616d"
ORANGE = "#f59e42"
SELECT = "#1d3557"
SCROLL = "#3a4864"          # scrollbar thumb
SCROLL_HOVER = "#566a90"

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

    # buttons: flat, no bevel
    s.configure("TButton", background=PANEL2, foreground=FG, padding=(10, 5), borderwidth=1, relief="flat",
                bordercolor=BORDER, lightcolor=PANEL2, darkcolor=PANEL2)
    s.map("TButton", background=[("active", PANEL3), ("pressed", ACCENT)],
          lightcolor=[("active", PANEL3)], darkcolor=[("active", PANEL3)])
    s.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT,
                lightcolor=ACCENT, darkcolor=ACCENT)
    s.map("Accent.TButton", background=[("active", ACCENT_DK), ("pressed", "#2d62c4")],
          lightcolor=[("active", ACCENT_DK)], darkcolor=[("active", ACCENT_DK)],
          bordercolor=[("active", ACCENT_DK)])
    s.configure("Pick.TButton", background=PANEL3, foreground=FG, bordercolor=BORDER, lightcolor=PANEL3,
                darkcolor=PANEL3, padding=(14, 5))
    s.map("Pick.TButton", background=[("active", SCROLL)], lightcolor=[("active", SCROLL)],
          darkcolor=[("active", SCROLL)])
    s.configure("Danger.TButton", background="#3a1f24", foreground="#fca5a5")
    s.map("Danger.TButton", background=[("active", "#5a2a31")])
    s.configure("Seg.TButton", background=PANEL2, foreground=MUTED, padding=(14, 5))
    s.configure("SegOn.TButton", background=ACCENT, foreground="white", padding=(14, 5), bordercolor=ACCENT,
                lightcolor=ACCENT, darkcolor=ACCENT)
    s.map("SegOn.TButton", background=[("active", ACCENT_DK)])

    # tabs: the clam theme grows / re-pads the *selected* tab, which makes the tab bar jump when you switch
    # tabs. Pin padding and expand so every tab keeps exactly the same size and position.
    tab_pad = [22, 10, 22, 10]
    s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(8, 8, 8, 0), bordercolor=BORDER,
                lightcolor=BG, darkcolor=BG)
    s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=tab_pad, font=(ui, 10, "bold"),
                bordercolor=BORDER, lightcolor=PANEL, darkcolor=PANEL)
    s.map("TNotebook.Tab",
          background=[("selected", PANEL2), ("active", PANEL3), ("!selected", PANEL)],
          foreground=[("selected", FG), ("active", FG), ("!selected", MUTED)],
          lightcolor=[("selected", PANEL2), ("active", PANEL3), ("!selected", PANEL)],
          darkcolor=[("selected", PANEL2), ("active", PANEL3), ("!selected", PANEL)],
          bordercolor=[("selected", BORDER), ("!selected", BORDER)],
          padding=[("selected", tab_pad), ("!selected", tab_pad)],
          expand=[("selected", [0, 0, 0, 0]), ("!selected", [0, 0, 0, 0])])

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

    # scrollbars: slim, arrow-less, with a clearly visible *solid* thumb. (Before, the thumb was almost the
    # same colour as the trough and only its outline showed, so it looked hollow.)
    for orient, sticky in (("Vertical", "ns"), ("Horizontal", "ew")):
        name = f"{orient}.TScrollbar"
        s.layout(name, [(f"{orient}.Scrollbar.trough", {"sticky": sticky, "children": [
            (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        s.configure(name, background=SCROLL, darkcolor=SCROLL, lightcolor=SCROLL, bordercolor=BG,
                    troughcolor=BG, relief="flat", gripcount=0, arrowsize=12, width=12)
        s.map(name,
              background=[("pressed", SCROLL_HOVER), ("active", SCROLL_HOVER)],
              darkcolor=[("pressed", SCROLL_HOVER), ("active", SCROLL_HOVER)],
              lightcolor=[("pressed", SCROLL_HOVER), ("active", SCROLL_HOVER)])
    s.configure("TPanedwindow", background=BG)

    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.font", (ui, 10))


def style_text(w: tk.Text, font=None) -> None:
    w.configure(bg=PANEL2, fg=FG, insertbackground=FG, selectbackground=ACCENT, selectforeground="white",
                relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                padx=8, pady=6, wrap="word", font=font or (F["ui"], 10), undo=True)
