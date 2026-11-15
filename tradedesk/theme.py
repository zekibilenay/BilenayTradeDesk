"""Colours, fonts and the ttk styling. Several themes can be switched live (see `set_theme` / `recolor`).

Every colour in the UI is one of the *roles* below (BG, PANEL, FG, ACCENT, ...). The module-level names
(`theme.BG`, `theme.FG`, ...) always hold the colours of the current theme, so code should read them when it
draws a widget and never keep a copy.
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

F = {"ui": "Segoe UI", "mono": "Consolas"}

# ---- palettes -------------------------------------------------------------------------------------------
# Only the base roles are listed; the rest (hover colours, tinted banners, dimmed calendar rows ...) is derived
# in `_build` so that every theme stays consistent and readable.
THEMES = {
    "Midnight": dict(BG="#0d1117", PANEL="#151b24", PANEL2="#1c2431", PANEL3="#263044", BORDER="#2a3548",
                     FG="#e6edf3", MUTED="#97a3b6", ACCENT="#5b9bff", GREEN="#34c77b", YELLOW="#e5b73b",
                     RED="#f0707b", ORANGE="#f59e42", SELECT="#1d3557", SCROLL="#3a4864",
                     SCROLL_HOVER="#566a90", IMP_HIGH="#ff7b7b", IMP_MED="#f5b04c", IMP_LOW="#aab1bf"),
    "Graphite": dict(BG="#141416", PANEL="#1c1c1f", PANEL2="#252529", PANEL3="#303036", BORDER="#3a3a42",
                     FG="#ececf0", MUTED="#a2a2ae", ACCENT="#7db1ff", GREEN="#3ecf8e", YELLOW="#e8c14a",
                     RED="#f27f7f", ORANGE="#f5a04a", SELECT="#33425e", SCROLL="#4a4a55",
                     SCROLL_HOVER="#6a6a78", IMP_HIGH="#ff8080", IMP_MED="#f5b04c", IMP_LOW="#b4b4c0"),
    "OLED Black": dict(BG="#000000", PANEL="#0a0a0a", PANEL2="#141414", PANEL3="#1f1f1f", BORDER="#2c2c2c",
                       FG="#f2f2f2", MUTED="#a0a0a0", ACCENT="#62a8ff", GREEN="#3ddc84", YELLOW="#f0c24a",
                       RED="#ff7a7a", ORANGE="#ffa24a", SELECT="#17305a", SCROLL="#3a3a3a",
                       SCROLL_HOVER="#5c5c5c", IMP_HIGH="#ff8585", IMP_MED="#ffb44d", IMP_LOW="#b5b5b5"),
    "Nord": dict(BG="#2b303b", PANEL="#323846", PANEL2="#3a4150", PANEL3="#465065", BORDER="#4f5a70",
                 FG="#eceff4", MUTED="#c0cadc", ACCENT="#8fc7da", GREEN="#a6c98c", YELLOW="#ecd08f",
                 RED="#f0929b", ORANGE="#f0b27e", SELECT="#3d4b68", SCROLL="#5a6580",
                 SCROLL_HOVER="#7a87a6", IMP_HIGH="#f9aab2", IMP_MED="#f0b27e", IMP_LOW="#c4cddc"),
    "Light": dict(BG="#eef1f6", PANEL="#ffffff", PANEL2="#f1f4f9", PANEL3="#e1e7f1", BORDER="#c3cbdb",
                  FG="#18202e", MUTED="#505c72", ACCENT="#1d5fd0", GREEN="#13783a", YELLOW="#856000",
                  RED="#c12a38", ORANGE="#ad4d00", SELECT="#cfe0ff", SCROLL="#9aa7bf",
                  SCROLL_HOVER="#7b8aa6", IMP_HIGH="#c12a38", IMP_MED="#984e00", IMP_LOW="#586175"),
    "Sand": dict(BG="#f2ebdc", PANEL="#fffaf0", PANEL2="#f4ecda", PANEL3="#e9dec6", BORDER="#cdbf9f",
                 FG="#2a2417", MUTED="#665a42", ACCENT="#9c4a0e", GREEN="#2b6b2b", YELLOW="#765600",
                 RED="#b02419", ORANGE="#9a4a00", SELECT="#f0d9ae", SCROLL="#b3a381",
                 SCROLL_HOVER="#94855f", IMP_HIGH="#b02419", IMP_MED="#935000", IMP_LOW="#615640"),
}
DEFAULT_THEME = "Midnight"

ROLES = ("BG", "PANEL", "PANEL2", "PANEL3", "BORDER", "FG", "MUTED", "ACCENT", "ACCENT_BTN", "ACCENT_HOVER",
         "ACCENT_PRESS", "ACCENT_BG", "ACCENT_DIM", "GREEN", "YELLOW", "RED", "RED_BTN", "ORANGE", "SELECT",
         "SCROLL", "SCROLL_HOVER", "IMP_HIGH", "IMP_MED", "IMP_LOW", "IMP_HIGH_DIM", "IMP_MED_DIM",
         "IMP_LOW_DIM", "SOON_BG", "INVALID_BG")


# ---- colour maths ---------------------------------------------------------------------------------------
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    """t=0 -> a, t=1 -> b."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex([x + (y - x) * t for x, y in zip(ra, rb)])


def luminance(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _darken_until(color, against="#ffffff", target=4.5):
    """Darken `color` until `against` text on it reaches the contrast `target` (used for button fills)."""
    c = color
    for _ in range(40):
        if contrast(c, against) >= target:
            return c
        c = mix(c, "#000000", 0.06)
    return c


def _dim(color, bg, target=3.2):
    """A visibly de-emphasised version of `color` that still reaches `target` contrast on `bg`."""
    for t in (0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.0):
        c = mix(color, bg, t)
        if contrast(c, bg) >= target:
            return c
    return color


def _build(base: dict) -> dict:
    p = dict(base)
    p["ACCENT_BTN"] = _darken_until(p["ACCENT"])
    p["ACCENT_HOVER"] = mix(p["ACCENT_BTN"], "#000000", 0.14)
    p["ACCENT_PRESS"] = mix(p["ACCENT_BTN"], "#000000", 0.26)
    p["ACCENT_BG"] = mix(p["PANEL"], p["ACCENT"], 0.16)
    p["ACCENT_DIM"] = mix(p["PANEL"], p["ACCENT"], 0.45)
    p["RED_BTN"] = _darken_until(p["RED"])
    for k in ("HIGH", "MED", "LOW"):
        p[f"IMP_{k}_DIM"] = _dim(p[f"IMP_{k}"], p["PANEL"])
    p["SOON_BG"] = mix(p["PANEL"], p["YELLOW"], 0.14)
    p["INVALID_BG"] = mix(p["PANEL2"], p["RED"], 0.2)
    # every role gets its own distinct value, so a colour can be mapped back to its role when switching themes
    # (pure white / black are reserved for text on buttons and Tk's own defaults, so no role may use them)
    seen = {"#ffffff": "white", "#000000": "black"}
    for r in ROLES:
        v = p[r].lower()
        while v in seen:
            ch = _rgb(v)
            v = _hex((ch[0], ch[1], ch[2] + 1 if ch[2] < 255 else ch[2] - 1))
        seen[v] = r
        p[r] = v
    return {r: p[r] for r in ROLES}


_current = DEFAULT_THEME
_listeners = []


def names():
    return list(THEMES)


def current_name():
    return _current


def palette(name=None) -> dict:
    return _build(THEMES[name or _current])


def set_theme(name):
    """Make `name` the current theme (updates theme.BG, theme.FG ...). Returns the new palette."""
    global _current
    if name not in THEMES:
        name = DEFAULT_THEME
    _current = name
    pal = palette(name)
    globals().update(pal)
    return pal


def on_change(fn):
    """Register fn() to run after the theme was switched (for colours that live outside of widget options)."""
    _listeners.append(fn)


set_theme(DEFAULT_THEME)


# ---- switching the theme of a running window -------------------------------------------------------------
_COLOR_OPTIONS = ("background", "foreground", "highlightbackground", "highlightcolor", "insertbackground",
                  "selectbackground", "selectforeground", "activebackground", "activeforeground",
                  "disabledforeground", "troughcolor", "readonlybackground")


def recolor(root, old: dict, new: dict) -> None:
    """Re-colour every existing widget: a widget option that holds a colour of the old theme gets the colour of
    the same role in the new theme. Nothing is rebuilt, so scroll positions and typed text stay as they are."""
    mapping = {old[r].lower(): new[r] for r in old if old[r].lower() != new[r].lower()}

    def fix(w):
        try:
            keys = w.keys()
        except (tk.TclError, AttributeError):
            return
        for opt in _COLOR_OPTIONS:
            if opt in keys:
                try:
                    cur = str(w.cget(opt)).lower()
                    if cur in mapping:
                        w.configure(**{opt: mapping[cur]})
                except tk.TclError:
                    pass
        stored = getattr(w, "_bg", None)
        if isinstance(stored, str) and stored.lower() in mapping:
            w._bg = mapping[stored.lower()]

    def walk(w):
        fix(w)
        for c in w.winfo_children():
            walk(c)
    walk(root)
    for fn in list(_listeners):
        try:
            fn()
        except tk.TclError:
            pass


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
    """(Re)configure the root window and all ttk styles from the current palette."""
    F["ui"] = _pick(root, ["Segoe UI", "Helvetica Neue", "Ubuntu", "Noto Sans", "Cantarell", "DejaVu Sans",
                           "Liberation Sans", "Arial"], "TkDefaultFont")
    F["mono"] = _pick(root, ["Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Courier New"], "TkFixedFont")
    ui = F["ui"]
    t = globals()

    root.configure(bg=t["BG"])
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=t["BG"], foreground=t["FG"], fieldbackground=t["PANEL2"], bordercolor=t["BORDER"],
                lightcolor=t["BG"], darkcolor=t["BG"], troughcolor=t["PANEL"], focuscolor=t["BG"], font=(ui, 10))
    s.configure("TFrame", background=t["BG"])
    s.configure("Panel.TFrame", background=t["PANEL"])
    s.configure("TLabel", background=t["BG"], foreground=t["FG"])
    s.configure("Muted.TLabel", foreground=t["MUTED"])
    s.configure("Title.TLabel", font=(ui, 13, "bold"))
    s.configure("TSeparator", background=t["BORDER"])

    # buttons: flat, no bevel
    s.configure("TButton", background=t["PANEL2"], foreground=t["FG"], padding=(10, 5), borderwidth=1,
                relief="flat", bordercolor=t["BORDER"], lightcolor=t["PANEL2"], darkcolor=t["PANEL2"])
    s.map("TButton", background=[("active", t["PANEL3"]), ("pressed", t["ACCENT_BTN"])],
          foreground=[("pressed", "#ffffff")],
          lightcolor=[("active", t["PANEL3"])], darkcolor=[("active", t["PANEL3"])])
    s.configure("Accent.TButton", background=t["ACCENT_BTN"], foreground="#ffffff", bordercolor=t["ACCENT_BTN"],
                lightcolor=t["ACCENT_BTN"], darkcolor=t["ACCENT_BTN"])
    s.map("Accent.TButton", background=[("active", t["ACCENT_HOVER"]), ("pressed", t["ACCENT_PRESS"])],
          foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
          lightcolor=[("active", t["ACCENT_HOVER"])], darkcolor=[("active", t["ACCENT_HOVER"])],
          bordercolor=[("active", t["ACCENT_HOVER"])])
    s.configure("Pick.TButton", background=t["PANEL3"], foreground=t["FG"], bordercolor=t["BORDER"],
                lightcolor=t["PANEL3"], darkcolor=t["PANEL3"], padding=(14, 5))
    s.map("Pick.TButton", background=[("active", t["SCROLL"])], foreground=[("active", t["FG"])],
          lightcolor=[("active", t["SCROLL"])], darkcolor=[("active", t["SCROLL"])])
    s.configure("Seg.TButton", background=t["PANEL2"], foreground=t["MUTED"], padding=(14, 5))
    s.configure("SegOn.TButton", background=t["ACCENT_BTN"], foreground="#ffffff", padding=(14, 5),
                bordercolor=t["ACCENT_BTN"], lightcolor=t["ACCENT_BTN"], darkcolor=t["ACCENT_BTN"])
    s.map("SegOn.TButton", background=[("active", t["ACCENT_HOVER"])], foreground=[("active", "#ffffff")])

    # tabs: the clam theme grows / re-pads the *selected* tab, which makes the tab bar jump when you switch
    # tabs. Pin padding and expand so every tab keeps exactly the same size and position.
    tab_pad = [22, 10, 22, 10]
    s.configure("TNotebook", background=t["BG"], borderwidth=0, tabmargins=(8, 8, 8, 0), bordercolor=t["BORDER"],
                lightcolor=t["BG"], darkcolor=t["BG"])
    s.configure("TNotebook.Tab", background=t["PANEL"], foreground=t["MUTED"], padding=tab_pad,
                font=(ui, 10, "bold"), bordercolor=t["BORDER"], lightcolor=t["PANEL"], darkcolor=t["PANEL"])
    s.map("TNotebook.Tab",
          background=[("selected", t["PANEL2"]), ("active", t["PANEL3"]), ("!selected", t["PANEL"])],
          foreground=[("selected", t["FG"]), ("active", t["FG"]), ("!selected", t["MUTED"])],
          lightcolor=[("selected", t["PANEL2"]), ("active", t["PANEL3"]), ("!selected", t["PANEL"])],
          darkcolor=[("selected", t["PANEL2"]), ("active", t["PANEL3"]), ("!selected", t["PANEL"])],
          bordercolor=[("selected", t["BORDER"]), ("!selected", t["BORDER"])],
          padding=[("selected", tab_pad), ("!selected", tab_pad)],
          expand=[("selected", [0, 0, 0, 0]), ("!selected", [0, 0, 0, 0])])

    s.configure("Treeview", background=t["PANEL"], fieldbackground=t["PANEL"], foreground=t["FG"], rowheight=26,
                borderwidth=0, font=(ui, 10))
    s.configure("Treeview.Heading", background=t["PANEL2"], foreground=t["MUTED"], relief="flat",
                font=(ui, 9, "bold"))
    s.map("Treeview", background=[("selected", t["SELECT"])], foreground=[("selected", t["FG"])])
    s.map("Treeview.Heading", background=[("active", t["PANEL2"])])

    s.configure("TCheckbutton", background=t["BG"], foreground=t["FG"], indicatorbackground=t["PANEL2"],
                indicatorforeground=t["FG"])
    s.map("TCheckbutton", background=[("active", t["BG"])], indicatorcolor=[("selected", t["ACCENT_BTN"])],
          indicatorbackground=[("selected", t["ACCENT_BTN"])])
    s.configure("TEntry", fieldbackground=t["PANEL2"], foreground=t["FG"], insertcolor=t["FG"], padding=4)
    s.configure("Invalid.TEntry", fieldbackground=t["INVALID_BG"], foreground=t["FG"], insertcolor=t["FG"], padding=4)
    s.configure("TCombobox", fieldbackground=t["PANEL2"], background=t["PANEL2"], foreground=t["FG"],
                arrowcolor=t["MUTED"], padding=4, selectbackground=t["ACCENT_BTN"], selectforeground="#ffffff")
    # readonly comboboxes must not show a highlighted (selected) text block after choosing a value
    s.map("TCombobox",
          fieldbackground=[("readonly", t["PANEL2"])], foreground=[("readonly", t["FG"])],
          selectbackground=[("readonly", t["PANEL2"])], selectforeground=[("readonly", t["FG"])])
    s.configure("TSpinbox", fieldbackground=t["PANEL2"], foreground=t["FG"], arrowcolor=t["MUTED"], padding=3)

    # scrollbars: slim, arrow-less, with a clearly visible *solid* thumb
    for orient, sticky in (("Vertical", "ns"), ("Horizontal", "ew")):
        name = f"{orient}.TScrollbar"
        s.layout(name, [(f"{orient}.Scrollbar.trough", {"sticky": sticky, "children": [
            (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        s.configure(name, background=t["SCROLL"], darkcolor=t["SCROLL"], lightcolor=t["SCROLL"],
                    bordercolor=t["BG"], troughcolor=t["BG"], relief="flat", gripcount=0, arrowsize=12, width=12)
        s.map(name,
              background=[("pressed", t["SCROLL_HOVER"]), ("active", t["SCROLL_HOVER"])],
              darkcolor=[("pressed", t["SCROLL_HOVER"]), ("active", t["SCROLL_HOVER"])],
              lightcolor=[("pressed", t["SCROLL_HOVER"]), ("active", t["SCROLL_HOVER"])])
    s.configure("TPanedwindow", background=t["BG"])
    s.configure("Sash", background=t["BORDER"], bordercolor=t["BG"], lightcolor=t["BORDER"], darkcolor=t["BORDER"],
                gripcount=0, sashthickness=6)

    root.option_add("*TCombobox*Listbox.background", t["PANEL2"])
    root.option_add("*TCombobox*Listbox.foreground", t["FG"])
    root.option_add("*TCombobox*Listbox.selectBackground", t["ACCENT_BTN"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", (ui, 10))


def style_text(w: tk.Text, font=None) -> None:
    w.configure(bg=PANEL2, fg=FG, insertbackground=FG, selectbackground=ACCENT_BTN, selectforeground="#ffffff",
                relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                padx=8, pady=6, wrap="word", font=font or (F["ui"], 10), undo=True)
