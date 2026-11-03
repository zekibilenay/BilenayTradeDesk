"""Trade Journal tab: one scrolling feed. Every trade is a card with its fields, big annotated
screenshots (HTF / LTF / DXY ...), the reasoning and the review. Everything autosaves."""
import re
import shutil
import tkinter as tk
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageTk

from . import theme
from .checklist_model import VERDICT_LABELS
from .paths import IMAGES_DIR
from .widgets import ConfirmButton, ScrollFrame, bind_autosize

KINDS = ["HTF", "LTF", "DXY HTF", "DXY LTF", "Entry", "Result", "Other"]
OUTCOMES = ["Open", "Win", "Loss", "BE"]
DIRECTIONS = ["", "Long", "Short"]
SESSIONS = ["", "Asia", "London", "New York", "London/NY overlap", "Other"]
THUMB = (540, 320)
PAGE = 10
THUMB_DIR = IMAGES_DIR / ".thumbs"
OUT_COLORS = {"Win": theme.GREEN, "Loss": theme.RED, "BE": theme.YELLOW, "Open": theme.MUTED}
NUM_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def r_value(text):
    m = NUM_RE.search(text or "")
    return float(m.group().replace(",", ".")) if m else None


def thumb_photo(row):
    """Thumbnail for a trade image, cached on disk so big screenshots load fast next time."""
    cache = THUMB_DIR / f"{row['id']}.png"
    try:
        if cache.exists():
            im = Image.open(cache)
            im.load()
        else:
            im = Image.open(IMAGES_DIR / row["filename"])
            im.load()
            im.thumbnail(THUMB, Image.LANCZOS)
            try:
                THUMB_DIR.mkdir(parents=True, exist_ok=True)
                im.save(cache, "PNG")
            except OSError:
                pass
    except Exception:
        im = Image.new("RGB", (THUMB[0], 120), "#222")
    return ImageTk.PhotoImage(im)


class ImageViewer(tk.Toplevel):
    """Full-size viewer: ←/→ to browse, Esc to close."""

    def __init__(self, master, items, index):
        super().__init__(master)
        self.configure(bg="black")
        self.items, self.index, self.photo = items, index, None
        self.lbl = tk.Label(self, bg="black", cursor="hand2")
        self.lbl.pack(fill="both", expand=True)
        self.cap = tk.Label(self, bg="#111", fg="white", font=(theme.F["ui"], 11), pady=6)
        self.cap.pack(fill="x")
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Left>", lambda e: self._go(-1))
        self.bind("<Right>", lambda e: self._go(1))
        self.lbl.bind("<Button-1>", lambda e: self._go(1))
        self.focus_set()
        self._show()

    def _go(self, d):
        self.index = (self.index + d) % len(self.items)
        self._show()

    def _show(self):
        path, title = self.items[self.index]
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        try:
            im = Image.open(path)
            im.load()
            im.thumbnail((int(sw * 0.92), int(sh * 0.84)), Image.LANCZOS)
        except Exception:
            im = Image.new("RGB", (600, 300), "#222")
        self.photo = ImageTk.PhotoImage(im)
        self.lbl.configure(image=self.photo)
        self.cap.configure(text=f"{title}   ({self.index + 1}/{len(self.items)})   ←/→ browse · Esc close")
        self.title(title)
        w, h = im.size
        self.geometry(f"{w}x{h + 40}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")


class TradeCard(tk.Frame):
    TEXT_KEYS = ("trade_date", "trade_time", "instrument", "direction", "session", "entry", "sl", "tp",
                 "exit_price", "outcome", "result_r", "setup", "dxy_conf", "mistakes")

    def __init__(self, master, tab, row):
        super().__init__(master, bg=theme.PANEL, highlightthickness=2, highlightbackground=theme.BORDER)
        self.tab, self.db, self.id = tab, tab.db, row["id"]
        self.vars, self.widgets, self._job = {}, {}, None
        self.loading = True
        self._build(row)
        self.loading = False
        self._bind_active(self)

    def destroy(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        super().destroy()

    # ------------------------------------------------------------------ build
    def _field(self, parent, label, key, kind="entry", width=12, values=None, editable=False):
        f = tk.Frame(parent, bg=theme.PANEL)
        tk.Label(f, text=label.upper(), bg=theme.PANEL, fg=theme.MUTED, font=(theme.F["ui"], 8, "bold"),
                 anchor="w").pack(fill="x")
        var = tk.StringVar()
        self.vars[key] = var
        if kind == "entry":
            w = ttk.Entry(f, textvariable=var, width=width)
        else:
            w = ttk.Combobox(f, textvariable=var, values=values or [], width=width, exportselection=False,
                             state="normal" if editable else "readonly")
            self.tab.feed.guard_wheel(w)
        w.pack(fill="x", pady=(3, 0))
        self.widgets[key] = w
        var.trace_add("write", self._changed)
        return f

    def _build(self, row):
        ui = theme.F["ui"]
        self.strip = tk.Frame(self, bg=theme.MUTED, width=6)
        self.strip.pack(side="left", fill="y")
        body = tk.Frame(self, bg=theme.PANEL)
        body.pack(side="left", fill="both", expand=True, padx=16, pady=14)

        # --- row 1: identity
        r1 = tk.Frame(body, bg=theme.PANEL)
        r1.pack(fill="x")
        self.title_lbl = tk.Label(r1, text=f"TRADE #{self.id}", bg=theme.PANEL, fg=theme.ACCENT,
                                  font=(ui, 12, "bold"))
        self.title_lbl.pack(side="left", padx=(0, 16), anchor="s")
        for label, key, kind, width, vals, ed in (
                ("Date (YYYY-MM-DD)", "trade_date", "entry", 13, None, False),
                ("Time (HH:MM)", "trade_time", "entry", 8, None, False),
                ("Pair", "instrument", "entry", 9, None, False),
                ("Direction", "direction", "combo", 8, DIRECTIONS, False),
                ("Session", "session", "combo", 17, SESSIONS, False)):
            self._field(r1, label, key, kind, width, vals, ed).pack(side="left", padx=(0, 10))
        ConfirmButton(r1, command=lambda: self.tab.delete_trade(self), text="Delete trade",
                      armed_text="Click again to delete", bg=theme.PANEL).pack(side="right", anchor="s")
        self.status = tk.Label(r1, text="", bg=theme.PANEL, fg=theme.GREEN, font=(ui, 9))
        self.status.pack(side="right", padx=10, anchor="s")

        # --- row 2: result + tags
        r2 = tk.Frame(body, bg=theme.PANEL)
        r2.pack(fill="x", pady=(10, 0))
        self._field(r2, "Outcome", "outcome", "combo", 9, OUTCOMES).pack(side="left", padx=(0, 10))
        self._field(r2, "Result (e.g. +2R)", "result_r", "entry", 10).pack(side="left", padx=(0, 10))
        cl = tk.Frame(r2, bg=theme.PANEL)
        cl.pack(side="left", padx=(0, 14))
        tk.Label(cl, text="CHECKLIST THAT DAY", bg=theme.PANEL, fg=theme.MUTED, font=(ui, 8, "bold"),
                 anchor="w").pack(fill="x")
        self.cl_lbl = tk.Label(cl, text="—", bg=theme.PANEL, fg=theme.MUTED, font=(ui, 11, "bold"), anchor="w")
        self.cl_lbl.pack(fill="x", pady=(5, 0))
        self._field(r2, "Setup", "setup", "combo", 22, self.db.distinct_values("setup"), True).pack(
            side="left", padx=(0, 10), fill="x", expand=True)
        self._field(r2, "DXY confirmation", "dxy_conf", "combo", 22, self.db.distinct_values("dxy_conf"), True).pack(
            side="left", padx=(0, 10), fill="x", expand=True)
        self._field(r2, "Mistakes", "mistakes", "entry", 22).pack(side="left", fill="x", expand=True)

        # --- row 3: free-text levels (liquidity names etc.)
        r3 = tk.Frame(body, bg=theme.PANEL)
        r3.pack(fill="x", pady=(10, 0))
        for i, (label, key) in enumerate((("Entry", "entry"), ("Stop", "sl"), ("Target", "tp"), ("Exit", "exit_price"))):
            r3.columnconfigure(i, weight=1, uniform="lv")
            self._field(r3, label, key, "entry", 10).grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))

        # --- images
        self._section_label(body, "CHARTS & SCREENSHOTS")
        bar = tk.Frame(body, bg=theme.PANEL)
        bar.pack(fill="x")
        tk.Label(bar, text="Type of next image:", bg=theme.PANEL, fg=theme.MUTED, font=(ui, 9)).pack(side="left")
        self.kind_var = tk.StringVar(value=KINDS[0])
        kcb = ttk.Combobox(bar, textvariable=self.kind_var, values=KINDS, state="readonly", width=10,
                           exportselection=False)
        kcb.pack(side="left", padx=(6, 12))
        self.tab.feed.guard_wheel(kcb)
        ttk.Button(bar, text="Paste screenshot (Ctrl+V)", style="Accent.TButton", command=self.paste).pack(side="left")
        ttk.Button(bar, text="Add file…", command=self.add_files).pack(side="left", padx=(8, 0))
        self.gallery = tk.Frame(body, bg=theme.PANEL)
        self.gallery.pack(fill="x", pady=(8, 0), anchor="w")

        # --- reasoning + review
        self._section_label(body, "WHY I TOOK THIS TRADE")
        self.why = tk.Text(body, height=4, width=10)
        theme.style_text(self.why, (ui, 11))
        self.why.pack(fill="x")
        bind_autosize(self.why, 4, 40)
        self._section_label(body, "REVIEW — WHAT HAPPENED, WHAT I LEARNED")
        self.review = tk.Text(body, height=4, width=10)
        theme.style_text(self.review, (ui, 11))
        self.review.pack(fill="x")
        bind_autosize(self.review, 4, 40)

        # --- fill values
        for k in self.TEXT_KEYS:
            self.vars[k].set(row.get(k) or "")
        self.why.insert("1.0", row.get("why", ""))
        self.review.insert("1.0", row.get("review", ""))
        self.why.bind("<KeyRelease>", self._changed, add="+")
        self.review.bind("<KeyRelease>", self._changed, add="+")
        self._update_cl_label(row.get("cl_verdict", ""), row.get("cl_score"))
        self._update_strip()
        self.render_gallery()

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, bg=theme.PANEL, fg=theme.ACCENT, font=(theme.F["ui"], 9, "bold"),
                 anchor="w").pack(fill="x", pady=(16, 5))

    def _bind_active(self, widget):
        widget.bind("<FocusIn>", lambda e: self.tab.set_active(self), add="+")
        widget.bind("<Button-1>", lambda e: self.tab.set_active(self), add="+")
        for child in widget.winfo_children():
            self._bind_active(child)

    # ------------------------------------------------------------- saving
    def _changed(self, *_):
        if self.loading:
            return
        self.status.configure(text="…", fg=theme.MUTED)
        self._update_strip()
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(700, self.save)

    def flush(self):
        if self._job:
            self.save()

    @staticmethod
    def _valid(text, fmt):
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            return False

    def save(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        v = {k: self.vars[k].get().strip() for k in self.TEXT_KEYS}
        date_ok = self._valid(v["trade_date"], "%Y-%m-%d")
        time_ok = v["trade_time"] == "" or self._valid(v["trade_time"], "%H:%M")
        self.widgets["trade_date"].configure(style="TEntry" if date_ok else "Invalid.TEntry")
        self.widgets["trade_time"].configure(style="TEntry" if time_ok else "Invalid.TEntry")
        fields = {k: v[k] for k in self.TEXT_KEYS if not (k == "trade_date" and not date_ok)
                  and not (k == "trade_time" and not time_ok)}
        fields["instrument"] = v["instrument"] or "EURUSD"
        fields["why"] = self.why.get("1.0", "end-1c").strip()
        fields["review"] = self.review.get("1.0", "end-1c").strip()
        day = v["trade_date"] if date_ok else (self.db.get_trade(self.id) or {}).get("trade_date", "")
        rec = self.db.get_checklist_day(day) if day else None
        fields["cl_verdict"] = rec["verdict"] if rec else ""
        fields["cl_score"] = rec["score"] if rec else None
        self.db.update_trade(self.id, fields)
        self._update_cl_label(fields["cl_verdict"], fields["cl_score"])
        if date_ok and time_ok:
            self.status.configure(text="✓ saved", fg=theme.GREEN)
        else:
            self.status.configure(text="date/time format not saved", fg=theme.ORANGE)
        self.tab.refresh_stats()

    def _update_strip(self):
        self.strip.configure(bg=OUT_COLORS.get(self.vars["outcome"].get(), theme.MUTED))

    def _update_cl_label(self, verdict, score):
        if not verdict:
            self.cl_lbl.configure(text="no record", fg=theme.MUTED)
        else:
            pct = f"  ({score:.0f}%)" if score is not None else ""
            self.cl_lbl.configure(text=VERDICT_LABELS.get(verdict, verdict) + pct,
                                  fg=theme.VERDICT_COLORS.get(verdict, theme.MUTED))

    # ------------------------------------------------------------- images
    def render_gallery(self):
        for w in self.gallery.winfo_children():
            w.destroy()
        rows = self.db.list_images(self.id)
        if not rows:
            tk.Label(self.gallery, bg=theme.PANEL, fg=theme.MUTED, font=(theme.F["ui"], 10), justify="left",
                     text="No screenshots yet. Choose the image type, take a screenshot (Win+Shift+S), "
                          "then press Ctrl+V.").grid(row=0, column=0, sticky="w", pady=6)
            return
        for idx, r in enumerate(rows):
            self._image_block(r, idx).grid(row=idx // 2, column=idx % 2, padx=(0, 14), pady=(0, 14), sticky="n")
        self._bind_active(self.gallery)

    def _image_block(self, r, idx):
        ui = theme.F["ui"]
        block = tk.Frame(self.gallery, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
        photo = self.tab.photo(r)
        lbl = tk.Label(block, image=photo, bg="#000", cursor="hand2")
        lbl.image = photo
        lbl.pack(padx=8, pady=(8, 6))
        lbl.bind("<Button-1>", lambda e, i=idx: self._open_viewer(i))

        line = tk.Frame(block, bg=theme.PANEL2)
        line.pack(fill="x", padx=8)
        kind_var = tk.StringVar(value=r["kind"])
        kcb = ttk.Combobox(line, textvariable=kind_var, values=KINDS, state="readonly", width=10, exportselection=False)
        kcb.pack(side="left")
        self.tab.feed.guard_wheel(kcb)
        kcb.bind("<<ComboboxSelected>>", lambda e, rid=r["id"], v=kind_var: (self.db.update_image(rid, kind=v.get()),
                                                                           kcb.selection_clear()))
        tk.Label(line, text="click image to enlarge", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 8)).pack(
            side="left", padx=10)
        ConfirmButton(line, command=lambda rid=r["id"]: self._delete_image(rid), text="Remove",
                      armed_text="Click again", bg=theme.PANEL2).pack(side="right")

        cap = tk.Text(block, height=2, width=10)
        theme.style_text(cap, (ui, 10))
        cap.pack(fill="x", padx=8, pady=(6, 8))
        cap.insert("1.0", r["caption"])
        bind_autosize(cap, 2, 12)
        cap.bind("<KeyRelease>", lambda e, rid=r["id"], w=cap: self.db.update_image(rid, caption=w.get("1.0", "end-1c")),
                 add="+")
        tk.Label(block, text="↑ describe what this chart shows", bg=theme.PANEL2, fg=theme.MUTED,
                 font=(ui, 8)).pack(anchor="w", padx=10, pady=(0, 6))
        return block

    def _open_viewer(self, idx):
        rows = self.db.list_images(self.id)
        items = [(IMAGES_DIR / r["filename"], r["kind"] + (f" — {r['caption']}" if r["caption"] else ""))
                 for r in rows]
        if items:
            ImageViewer(self.winfo_toplevel(), items, min(idx, len(items) - 1))

    def _delete_image(self, image_id):
        fn = self.db.delete_image(image_id)
        if fn:
            for p in (IMAGES_DIR / fn, THUMB_DIR / f"{image_id}.png"):
                try:
                    p.unlink()
                except OSError:
                    pass
        self.render_gallery()

    def _store(self, im):
        if im.mode not in ("RGB", "RGBA", "L"):
            im = im.convert("RGB")
        folder = IMAGES_DIR / f"trade_{self.id}"
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex[:12]}.png"
        im.save(folder / name, "PNG")
        self.db.add_image(self.id, self.kind_var.get(), "", f"trade_{self.id}/{name}")
        i = KINDS.index(self.kind_var.get()) if self.kind_var.get() in KINDS else 0
        if i < len(KINDS) - 2:                           # HTF -> LTF -> DXY HTF -> DXY LTF -> Entry -> Result
            self.kind_var.set(KINDS[i + 1])

    def add_files(self):
        paths = filedialog.askopenfilenames(parent=self, title="Choose images", filetypes=[
            ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("All files", "*.*")])
        added = False
        for p in paths:
            try:
                with Image.open(p) as im:
                    im.load()
                    self._store(im.copy())
                    added = True
            except Exception as exc:
                messagebox.showwarning("Image", f"Could not add {Path(p).name}:\n{exc}", parent=self)
        if added:
            self.render_gallery()

    def paste(self):
        try:
            clip = ImageGrab.grabclipboard()
        except Exception:
            clip = None
        added = False
        if isinstance(clip, Image.Image):
            self._store(clip)
            added = True
        elif isinstance(clip, (list, tuple)):             # files copied in Explorer
            for p in clip:
                try:
                    with Image.open(p) as im:
                        im.load()
                        self._store(im.copy())
                        added = True
                except Exception:
                    continue
        if added:
            self.render_gallery()
        else:
            self.status.configure(text="no image on the clipboard — take a screenshot first (Win+Shift+S)",
                                  fg=theme.ORANGE)
        return added


class JournalTab(ttk.Frame):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.cards, self.active, self.shown = [], None, PAGE
        self._photos = {}
        self._search_job = None
        self._build()
        self.reload()
        self.bind_all("<Control-v>", self._on_ctrl_v, add="+")

    # ------------------------------------------------------------------ UI
    def _build(self):
        bar = ttk.Frame(self, padding=(12, 10, 12, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="+ New trade", style="Accent.TButton", command=self.new_trade).pack(side="left")
        ttk.Label(bar, text="Outcome:", style="Muted.TLabel").pack(side="left", padx=(20, 6))
        self.f_outcome = tk.StringVar(value="All")
        cb = ttk.Combobox(bar, textvariable=self.f_outcome, values=["All"] + OUTCOMES, state="readonly", width=8,
                          exportselection=False)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: (cb.selection_clear(), self._filters_changed()))
        ttk.Label(bar, text="Search:", style="Muted.TLabel").pack(side="left", padx=(16, 6))
        self.f_search = tk.StringVar()
        ent = ttk.Entry(bar, textvariable=self.f_search, width=28)
        ent.pack(side="left")
        ent.bind("<KeyRelease>", lambda e: self._search_debounce())
        self.stats_lbl = ttk.Label(bar, text="", style="Muted.TLabel")
        self.stats_lbl.pack(side="right")
        self.feed = ScrollFrame(self, bg=theme.BG)
        self.feed.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 8))

    def _search_debounce(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(400, self._filters_changed)

    def _filters_changed(self):
        self.shown = PAGE
        self.reload(scroll_top=True)

    # -------------------------------------------------------------- feed
    def _query(self):
        outcome = self.f_outcome.get()
        return self.db.list_trades(outcome=None if outcome == "All" else outcome,
                                   search=self.f_search.get().strip() or None)

    def flush(self):
        for c in self.cards:
            try:
                c.flush()
            except tk.TclError:
                pass

    def reload(self, scroll_top=False, select_id=None):
        self.flush()
        for w in self.feed.inner.winfo_children():
            w.destroy()
        self.cards, self.active = [], None
        rows = self._query()
        self._update_stats(rows)
        if not rows:
            tk.Label(self.feed.inner, bg=theme.BG, fg=theme.MUTED, font=(theme.F["ui"], 12), pady=60,
                     text="No trades yet.\nClick “+ New trade” to start your journal.").pack(fill="x")
        for r in rows[:self.shown]:
            card = TradeCard(self.feed.inner, self, r)
            card.pack(fill="x", padx=(0, 14), pady=(10, 4))
            self.cards.append(card)
        remaining = len(rows) - self.shown
        if remaining > 0:
            ttk.Button(self.feed.inner, text=f"Show more ({remaining} older trades)",
                       command=self._show_more).pack(pady=16)
        else:
            tk.Frame(self.feed.inner, bg=theme.BG, height=24).pack()
        target = next((c for c in self.cards if c.id == select_id), None) or (self.cards[0] if self.cards else None)
        if target:
            self.set_active(target)
        if scroll_top:
            self.feed.scroll_top()

    def _show_more(self):
        keep = self.feed.canvas.yview()[0]
        self.shown += PAGE
        self.reload()
        self.after(60, lambda: self.feed.canvas.yview_moveto(keep))

    def _update_stats(self, rows):
        closed = [r for r in rows if r["outcome"] != "Open"]
        wins = sum(1 for r in closed if r["outcome"] == "Win")
        total_r = sum(v for v in (r_value(r["result_r"]) for r in rows) if v is not None)
        wr = f"{wins / len(closed) * 100:.0f}%" if closed else "—"
        self.stats_lbl.configure(text=f"{len(rows)} trades   •   Win rate: {wr}   •   Total R: {total_r:+.2f}")

    def refresh_stats(self):
        self._update_stats(self._query())

    def set_active(self, card):
        if self.active is card:
            return
        for c in self.cards:
            try:
                c.configure(highlightbackground=theme.ACCENT if c is card else theme.BORDER)
            except tk.TclError:
                pass
        self.active = card

    def photo(self, row):
        key = row["id"]
        if key not in self._photos:
            self._photos[key] = thumb_photo(row)
        return self._photos[key]

    # ------------------------------------------------------------ actions
    def new_trade(self):
        self.flush()
        now = datetime.now()
        tid = self.db.create_trade(now.strftime("%Y-%m-%d"), now.strftime("%H:%M"))
        self.f_outcome.set("All")
        self.f_search.set("")
        self.shown = max(self.shown, PAGE)
        self.reload(scroll_top=True, select_id=tid)

    def delete_trade(self, card):
        tid = card.id
        self.db.delete_trade(tid)
        shutil.rmtree(IMAGES_DIR / f"trade_{tid}", ignore_errors=True)
        self.reload()

    def _on_ctrl_v(self, _e):
        if not self.winfo_viewable() or not self.active:
            return
        focus = self.focus_get()
        if isinstance(focus, (tk.Text, tk.Entry, ttk.Entry, ttk.Combobox)):
            try:
                if self.clipboard_get():
                    return                                   # normal text paste, don't interfere
            except tk.TclError:
                pass                                         # no text on the clipboard -> maybe an image
        try:
            clip = ImageGrab.grabclipboard()
        except Exception:
            clip = None
        if clip is None:
            return
        self.active.paste()
        return "break"

    def save_current(self):
        self.flush()
