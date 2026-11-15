"""Announcement box of the Economic Calendar page.

Bilenay Trade Desk reads the same shared announcement feed as Next Book and Economic Calendar
(one JSON file on GitHub Pages) and shows it in a one-line box in the calendar toolbar:

  * announcements can not be dismissed; with several, the box rotates through them every 10 s ("1/3 ›")
  * a click opens the announcement board (every announcement as a card); links open only after you confirm
  * the feed is read once at start-up and again every 6 hours; failures are silent (nothing is shown)
  * set  "announcements": false  in data/settings.json to turn the whole thing off (no request is made)

The only network traffic is one HTTPS GET for the feed (User-Agent: BilenayTradeDesk/<version>); nothing
about you or your trades is sent.

Feed format (see https://github.com/zekibilenay/announcements): this app's id is "tradedesk".
    {"schema": 1, "apps": {"tradedesk": {"latest": "0.7.0", "url": "https://..."}},
     "announcements": [{"id", "apps": ["tradedesk" | "*"], "min_version", "max_version", "starts", "expires",
                        "priority", "type": "update|new_app|recommended|info", "text": {"en": "..."}, "url"}]}
"""
import datetime
import json
import math
import queue
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
import urllib.error
import urllib.request
import webbrowser
from tkinter import messagebox, ttk

from . import APP_NAME, APP_VERSION, theme
from .widgets import ScrollFrame

APP_ID = "tradedesk"                         # id used in the shared feed
FEED_URL = "https://zekibilenay.github.io/announcements/feed.json"
FALLBACK_URL = "https://bilenay.itch.io/"    # where an automatic "new version" announcement points to
REFRESH_MS = 6 * 60 * 60 * 1000              # ask again every 6 hours while the app stays open
ROTATE_MS = 10_000                           # rotation speed when there are several announcements
MAX_TEXT = 600
MAX_FEED_BYTES = 65536
ANN_TYPES = ("update", "new_app", "recommended", "info")
TYPE_NAMES = {"update": "Update", "new_app": "New app", "recommended": "Recommended app", "info": "Info"}


# ===================================================================== feed logic (no UI)
def feed_url():
    import os
    return os.environ.get("TRADEDESK_ANNOUNCE_URL", FEED_URL)


def parse_version(v):
    parts = re.findall(r"\d+", str(v))
    return tuple(int(x) for x in parts[:4]) or (0,)


def safe_url(u):
    """Only https links are accepted (the feed is remote data)."""
    u = str(u or "").strip()
    return u if u.lower().startswith("https://") and len(u) <= 500 else ""


def _loc(value, lang):
    """Pick the text in the user's language, then English, then any language. Keys like 'zh-CN' are accepted."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        by_lang = {}
        for k, v in value.items():
            if isinstance(v, str) and v.strip():
                by_lang.setdefault(str(k).strip().lower().replace("_", "-").split("-")[0], v)
        return by_lang.get(lang) or by_lang.get("en") or next(iter(by_lang.values()), "")
    return ""


class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect from https to http, so the "HTTPS only" promise can not be bypassed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith("https://"):
            raise urllib.error.URLError("redirect to a non-https url was blocked")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_feed(url=None):
    url = url or feed_url()
    if not url.lower().startswith("https://"):
        raise ValueError("announcement url must be https")
    req = urllib.request.Request(url, headers={"User-Agent": f"BilenayTradeDesk/{APP_VERSION}",
                                               "Accept": "application/json"})
    with urllib.request.build_opener(_HttpsOnlyRedirect).open(req, timeout=6) as r:
        raw = r.read(MAX_FEED_BYTES + 1)
    if len(raw) > MAX_FEED_BYTES:
        raise ValueError("announcement feed too large")
    return json.loads(raw.decode("utf-8"))


def select_announcements(feed, app_id=APP_ID, version=APP_VERSION, lang="en", today=None):
    """Announcements to show for this app + version + language, highest priority first."""
    out = []
    if not isinstance(feed, dict):
        return out
    today = today or datetime.date.today()
    cur = parse_version(version)

    apps = feed.get("apps")
    info = apps.get(app_id) if isinstance(apps, dict) else None
    if isinstance(info, dict) and info.get("latest") and parse_version(info["latest"]) > cur:
        out.append({"id": f"update-{app_id}-{info['latest']}", "type": "update", "priority": 1000,
                    "text": f"A new version is out: {info['latest']} (you have {version})",
                    "url": safe_url(info.get("url")) or FALLBACK_URL})

    items = feed.get("announcements")
    for a in (items if isinstance(items, list) else []):
        try:
            if not isinstance(a, dict):
                continue
            aid = str(a.get("id") or "")[:80]
            if not aid:
                continue
            targets = a.get("apps", ["*"])
            targets = [targets] if isinstance(targets, str) else list(targets)
            if "*" not in targets and app_id not in targets:
                continue
            if a.get("min_version") and cur < parse_version(a["min_version"]):
                continue
            if a.get("max_version") and cur > parse_version(a["max_version"]):
                continue
            if a.get("starts") and today < datetime.date.fromisoformat(str(a["starts"])):
                continue
            if a.get("expires") and today > datetime.date.fromisoformat(str(a["expires"])):
                continue
            text = " ".join(_loc(a.get("text"), lang).split())[:MAX_TEXT]
            if not text:
                continue
            kind = a.get("type") if a.get("type") in ANN_TYPES else "info"
            out.append({"id": aid, "type": kind, "text": text, "url": safe_url(a.get("url")),
                        "priority": int(a.get("priority", 0))})
        except (ValueError, TypeError):
            continue   # one broken entry must not block the others
    out.sort(key=lambda x: -x["priority"])   # stable: equal priorities keep the order of the file
    return out


def fit_text(font, text, px):
    """Shorten `text` with a trailing … so that it fits into `px` pixels."""
    if px <= 10 or font.measure(text) <= px:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(text[:mid].rstrip() + "…") <= px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"


# ===================================================================== round icons (drawn in code)
def _rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _star_points(cx, cy, R, rot_deg):
    pts = []
    for i in range(10):
        a = math.radians(rot_deg + i * 36)
        rad = R if i % 2 == 0 else R * 0.382
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    return pts


def _in_poly(x, y, pts):
    inside, j = False, len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def icon_rows(kind, size, fill, glyph, bg):
    """Round badge: info = i, update = arrow up, new_app = star, recommended = heart. 4x4 supersampling keeps the
    edge smooth. Rows are lists of '#rrggbb'. (Same drawing as in Next Book, so the apps look alike.)"""
    S = float(size)
    c = S / 2.0
    R = S / 2.0 - 0.5
    star = _star_points(c, c + S * 0.015, S * 0.30, 90)
    hs = S * 0.2368

    def in_glyph(x, y):
        if kind == "info":
            return ((x - c) ** 2 + (y - S * 0.31) ** 2 <= (S * 0.065) ** 2
                    or (abs(x - c) <= S * 0.065 and S * 0.45 <= y <= S * 0.76))
        if kind == "update":
            if abs(x - c) <= S * 0.07 and S * 0.48 <= y <= S * 0.76:
                return True
            return S * 0.24 <= y <= S * 0.50 and abs(x - c) <= (y - S * 0.24) * 0.21 / 0.26
        if kind == "new_app":
            return _in_poly(x, y, star)
        hx, hy = (x - c) / hs, -(y - c) / hs + 0.125      # recommended: heart curve
        return (hx * hx + hy * hy - 1) ** 3 - hx * hx * hy ** 3 <= 0

    cf, cg, cb = _rgb(fill), _rgb(glyph), _rgb(bg)
    n, rows = 4, []
    for py in range(size):
        row = []
        for px in range(size):
            r = g = b = 0
            for sy in range(n):
                for sx in range(n):
                    x, y = px + (sx + 0.5) / n, py + (sy + 0.5) / n
                    if (x - c) ** 2 + (y - c) ** 2 > R * R:
                        col = cb
                    elif in_glyph(x, y):
                        col = cg
                    else:
                        col = cf
                    r += col[0]
                    g += col[1]
                    b += col[2]
            k = n * n
            row.append("#%02x%02x%02x" % (round(r / k), round(g / k), round(b / k)))
        rows.append(row)
    return rows


def make_icon(kind, size, fill, glyph, bg):
    img = tk.PhotoImage(width=size, height=size)
    rows = icon_rows(kind, size, fill, glyph, bg)
    img.put(" ".join("{" + " ".join(r) + "}" for r in rows))
    return img


def icon_colors(kind):
    """(circle colour, symbol colour) in the current theme."""
    return {"update": (theme.ACCENT_BTN, "#ffffff"),
            "new_app": (theme.GREEN, theme.BG),
            "recommended": (theme.ORANGE, theme.BG)}.get(kind, (theme.MUTED, theme.BG))


def hover_bg():
    """Box colour while the mouse is over it: a touch of the accent colour, as much as the text stays readable."""
    for t in (0.16, 0.12, 0.09, 0.06, 0.04):
        c = theme.mix(theme.PANEL2, theme.ACCENT, t)
        if theme.contrast(theme.FG, c) >= 7 and theme.contrast(theme.MUTED, c) >= 4.5:
            return c
    return theme.PANEL2


# ===================================================================== the box in the toolbar
class AnnouncementBox(tk.Frame):
    """One-line announcement box. Stays invisible while there is nothing to show (offline, no matching entry)."""

    def __init__(self, master, enabled=True, loader=None, app_id=APP_ID, version=APP_VERSION, lang="en"):
        super().__init__(master, bg=theme.BG)
        self.enabled, self.app_id, self.version, self.lang = enabled, app_id, version, lang
        self.loader = loader or fetch_feed
        self.feed, self.items, self.idx = None, [], 0
        self._q = queue.Queue()
        self._worker = None
        self._rotate_job = self._poll_job = self._refresh_job = None
        self._over = False
        self._icons = {}
        ui = theme.F["ui"]
        self.font = tkfont.Font(family=ui, size=10)

        self.box = tk.Frame(self, bg=theme.PANEL2, bd=0, highlightthickness=1, highlightbackground=theme.ACCENT)
        self.more = tk.Label(self.box, text="›", font=(ui, 11, "bold"), cursor="hand2")
        self.more.pack(side="right", padx=(6, 10))
        self.icon = tk.Label(self.box, bd=0, cursor="hand2")
        self.icon.pack(side="left", padx=(10, 0))
        self.label = tk.Label(self.box, anchor="w", justify="left", width=1, font=(ui, 10), cursor="hand2")
        self.label.pack(side="left", fill="x", expand=True, padx=8, pady=3)
        self.label.bind("<Configure>", lambda e=None: self._fit())
        for w in (self.box, self.icon, self.label, self.more):
            w.bind("<Button-1>", lambda e=None: self.open_board())
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
        theme.on_change(self._on_theme)
        if enabled:
            self._start()

    def destroy(self):
        for job in (self._rotate_job, self._poll_job, self._refresh_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self._rotate_job = self._poll_job = self._refresh_job = None
        super().destroy()

    # ------------------------------------------------------------ fetching (worker thread never touches Tk)
    def _start(self):
        self._refresh_job = None
        if not self.enabled or (self._worker is not None and self._worker.is_alive()):
            return
        self._worker = threading.Thread(target=self._work, daemon=True)
        self._worker.start()
        self._poll_job = self.after(300, self._poll)

    def _work(self):
        try:
            self._q.put(("feed", self.loader()))
        except Exception:
            pass                                      # announcements are optional: never bother the user

    def _poll(self):
        self._poll_job = None
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == "feed":
                    self.set_feed(data)
        except queue.Empty:
            pass
        if self._worker is not None and self._worker.is_alive():
            self._poll_job = self.after(300, self._poll)
        else:
            self._refresh_job = self.after(REFRESH_MS, self._start)

    # ------------------------------------------------------------ showing
    def set_feed(self, feed):
        self.feed = feed
        self.items = select_announcements(feed, self.app_id, self.version, self.lang) if self.enabled else []
        self.idx = 0
        self._render()

    def _render(self):
        if self._rotate_job:
            try:
                self.after_cancel(self._rotate_job)
            except tk.TclError:
                pass
            self._rotate_job = None
        if not self.items:
            self.box.pack_forget()
            return
        if not self.box.winfo_ismapped():
            self.box.pack(fill="x")
        self.idx %= len(self.items)
        n = len(self.items)
        self.more.configure(text=f"{self.idx + 1}/{n}  ›" if n > 1 else "›")
        self._full = self.items[self.idx]["text"]
        self._paint()
        self._fit()
        if n > 1:
            self._rotate_job = self.after(ROTATE_MS, self._next)

    def _next(self):
        self._rotate_job = None
        self.idx += 1
        self._render()

    def _paint(self):
        """Colours of the box (the current theme; a little stronger while the mouse is over it)."""
        if not self.items:
            return
        bg = hover_bg() if self._over else theme.PANEL2
        kind = self.items[self.idx % len(self.items)]["type"]
        fill, glyph = icon_colors(kind)
        size = max(16, round(self.font.metrics("linespace") * 0.95))
        key = (kind, size, fill, glyph, bg)
        if key not in self._icons:
            if len(self._icons) > 40:
                self._icons.clear()
            self._icons[key] = make_icon(kind, size, fill, glyph, bg)
        try:
            self.configure(bg=theme.BG)
            self.box.configure(bg=bg, highlightbackground=theme.ACCENT)
            self.icon.configure(bg=bg, image=self._icons[key])
            self.label.configure(bg=bg, fg=theme.FG)
            self.more.configure(bg=bg, fg=theme.MUTED)
        except tk.TclError:
            pass

    def _on_theme(self):
        try:
            self._paint()
        except tk.TclError:
            pass

    def _fit(self):
        try:
            if self.items:
                self.label.configure(text=fit_text(self.font, self._full, self.label.winfo_width() - 16))
        except (tk.TclError, AttributeError):
            pass

    # hover highlight (delayed check, so moving between the child widgets does not flicker)
    def _enter(self, _e=None):
        self._over = True
        self._paint()

    def _leave(self, _e=None):
        self.after(40, self._check_leave)

    def _check_leave(self):
        try:
            w = self.winfo_containing(*self.winfo_pointerxy())
            box = str(self.box)
            inside = w is not None and (str(w) == box or str(w).startswith(box + "."))
        except (tk.TclError, KeyError, AttributeError):
            inside = False
        if inside != self._over:
            self._over = inside
            self._paint()

    def open_board(self):
        if self.items:
            AnnouncementBoard(self, self.items)


def open_url_confirmed(parent, text, url):
    """Announcement links come from the internet, so ask before opening one."""
    if messagebox.askyesno(APP_NAME, f"{text}\n\nOpen this link in your browser?\n{url}", parent=parent):
        webbrowser.open(url)


# ===================================================================== the board (all announcements as cards)
class AnnouncementBoard(tk.Toplevel):
    def __init__(self, box, items):
        super().__init__(box.winfo_toplevel())
        ui = theme.F["ui"]
        self.configure(bg=theme.PANEL)
        self.title("Announcements")
        self.transient(box.winfo_toplevel())
        self.minsize(440, 320)
        self._icons, self._labels = [], []

        head = tk.Frame(self, bg=theme.PANEL)
        head.pack(side="top", fill="x", padx=20, pady=(16, 8))
        tk.Label(head, text="Announcements", font=(ui, 16, "bold"), bg=theme.PANEL, fg=theme.FG).pack(side="left")
        tk.Label(head, text=str(len(items)), font=(ui, 9, "bold"), bg=theme.ACCENT_BTN, fg="#ffffff",
                 padx=8, pady=1).pack(side="left", padx=10)
        foot = tk.Frame(self, bg=theme.PANEL)
        foot.pack(side="bottom", fill="x", padx=20, pady=(8, 16))
        ttk.Button(foot, text="Close", style="Accent.TButton", command=self.destroy).pack(side="right")

        self.scroll = ScrollFrame(self, bg=theme.PANEL, wheel_px=60)
        self.scroll.pack(side="top", fill="both", expand=True, padx=(20, 8))
        self.scroll.canvas.bind("<Configure>", self._on_resize, add="+")
        icon_px = max(14, round(tkfont.Font(family=ui, size=10).metrics("linespace") * 0.95))
        for a in items:
            kind = a["type"] if a["type"] in ANN_TYPES else "info"
            fill, glyph = icon_colors(kind)
            card = tk.Frame(self.scroll.inner, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
            card.pack(fill="x", pady=(0, 10), padx=(0, 6))
            tk.Frame(card, bg=fill, width=5).pack(side="left", fill="y")
            body = tk.Frame(card, bg=theme.PANEL2)
            body.pack(side="left", fill="both", expand=True, padx=14, pady=10)
            row = tk.Frame(body, bg=theme.PANEL2)
            row.pack(fill="x")
            img = make_icon(kind, icon_px, fill, glyph, theme.PANEL2)
            self._icons.append(img)                                  # keep a reference or the icon disappears
            tk.Label(row, image=img, bg=theme.PANEL2, bd=0).pack(side="left")
            tk.Label(row, text=TYPE_NAMES.get(kind, "Info"), font=(ui, 9, "bold"), bg=theme.PANEL2, fg=theme.MUTED,
                     anchor="w").pack(side="left", padx=(8, 0))
            msg = tk.Label(body, text=a["text"], font=(ui, 10), bg=theme.PANEL2, fg=theme.FG, justify="left",
                           anchor="w", wraplength=480)
            msg.pack(fill="x", pady=(4, 0))
            self._labels.append(msg)
            if a.get("url"):
                ttk.Button(body, text="↗  Open link",
                           command=lambda u=a["url"], tx=a["text"]: open_url_confirmed(self, tx, u)
                           ).pack(anchor="w", pady=(8, 0))
        self.bind("<Escape>", lambda e=None: self.destroy())
        self._center(box.winfo_toplevel(), 620, 520)
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()

    def _on_resize(self, e):
        for lbl in self._labels:
            lbl.configure(wraplength=max(200, e.width - 90))

    def _center(self, parent, w, h):
        try:
            x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
            y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 3)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass
