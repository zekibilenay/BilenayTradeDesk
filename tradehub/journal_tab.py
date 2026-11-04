"""Trade Journal tab: one scrolling feed of trade cards.

A trade card has two looks:
  * EDITING  - every field is an input, everything autosaves, a "Finish" button at the bottom.
               A new trade always starts like this.
  * DONE     - a compact, read-only summary (result, levels, screenshots, reasoning, review) with an
               "Edit" button. This is what a finished trade looks like, so it no longer seems unfinished.
Screenshots are shown three per row; they have no description box (just the image type).
"""
import re
import shutil
import tkinter as tk
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageOps, ImageTk

from . import theme
from .checklist_model import VERDICT_LABELS
from .paths import IMAGES_DIR
from .widgets import ConfirmButton, ScrollFrame, bind_autosize

KINDS = ["HTF", "LTF", "DXY HTF", "DXY LTF", "Entry", "Result", "Other"]
OUTCOMES = ["Open", "Win", "Loss", "BE"]
DIRECTIONS = ["", "Long", "Short"]
SESSIONS = ["", "Asia", "London", "New York", "London/NY overlap", "Other"]
THUMB = (640, 400)                  # on-disk thumbnail cache size (max)
PAGE = 10
GALLERY_COLS = 3                    # screenshots per row
GALLERY_GAP = 12
IMG_RATIO = 0.58                    # screenshot box height / width
THUMB_DIR = IMAGES_DIR / ".thumbs"
OUT_COLORS = {"Win": theme.GREEN, "Loss": theme.RED, "BE": theme.YELLOW, "Open": theme.MUTED}
NUM_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def r_value(text):
    m = NUM_RE.search(text or "")
    return float(m.group().replace(",", ".")) if m else None


def thumb_image(row):
    """PIL thumbnail of a trade image, cached on disk so big screenshots load fast next time."""
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
    return im


def fit_photo(im, w, h):
    """Letterbox `im` into a black w x h box (so every screenshot cell has the same size)."""
    src = ImageOps.contain(im, (w, h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), "#000000")
    pos = ((w - src.width) // 2, (h - src.height) // 2)
    if src.mode in ("RGBA", "LA"):
        rgba = src.convert("RGBA")
        canvas.paste(rgba, pos, rgba)
    else:
        canvas.paste(src.convert("RGB"), pos)
    return ImageTk.PhotoImage(canvas)


def _chip(parent, text, fg, bg=None):
    return tk.Label(parent, text=text, fg=fg, bg=bg or theme.PANEL2, font=(theme.F["ui"], 9, "bold"),
                    padx=8, pady=2)


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


class Gallery(tk.Frame):
    """A trade's screenshots, three per row, sized to the width that is available."""

    def __init__(self, master, card, editable):
        super().__init__(master, bg=theme.PANEL)
        self.card, self.tab, self.editable = card, card.tab, editable
        self.rows, self._cw, self._job = [], 0, None
        self.bind("<Configure>", self._on_configure)

    def destroy(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        super().destroy()

    def set_rows(self, rows):
        self.rows = rows
        self._cw = 0
        self._draw()

    def _cell_width(self):
        total = self.winfo_width()
        if total < 150:                       # not laid out yet
            return 0
        return max(240, min(640, (total - GALLERY_GAP * (GALLERY_COLS - 1)) // GALLERY_COLS))

    def _on_configure(self, _e):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(80, self._draw_if_resized)

    def _draw_if_resized(self):
        self._job = None
        try:
            cw = self._cell_width()
            if cw and abs(cw - self._cw) >= 8:
                self._draw()
        except tk.TclError:
            pass

    def _draw(self):
        for w in self.winfo_children():
            w.destroy()
        if not self.rows:
            if self.editable:
                tk.Label(self, bg=theme.PANEL, fg=theme.MUTED, font=(theme.F["ui"], 10), justify="left",
                         text="No screenshots yet. Choose the image type, take a screenshot (Win+Shift+S), "
                              "then press Ctrl+V.").grid(row=0, column=0, sticky="w", pady=6)
            return
        cw = self._cell_width()
        if not cw:
            return                            # <Configure> will draw as soon as the width is known
        self._cw = cw
        iw = cw - 14
        ih = int(iw * IMG_RATIO)
        for c in range(GALLERY_COLS):
            self.columnconfigure(c, weight=1, uniform="gal")
        for idx, r in enumerate(self.rows):
            col = idx % GALLERY_COLS
            self._block(r, idx, iw, ih).grid(row=idx // GALLERY_COLS, column=col, sticky="nw",
                                             padx=(0 if col == 0 else GALLERY_GAP, 0), pady=(0, GALLERY_GAP))
        if self.editable:
            self.card.bind_active(self)

    def _block(self, r, idx, iw, ih):
        ui = theme.F["ui"]
        blk = tk.Frame(self, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
        photo = self.tab.photo(r, iw, ih)
        lbl = tk.Label(blk, image=photo, bg="#000", cursor="hand2", bd=0)
        lbl.image = photo
        lbl.pack(padx=6, pady=(6, 4))
        lbl.bind("<Button-1>", lambda e, i=idx: self.card.open_viewer(i))
        line = tk.Frame(blk, bg=theme.PANEL2)
        line.pack(fill="x", padx=6, pady=(0, 6))
        if self.editable:
            kind_var = tk.StringVar(value=r["kind"])
            kcb = ttk.Combobox(line, textvariable=kind_var, values=KINDS, state="readonly", width=10,
                               exportselection=False)
            kcb.pack(side="left")
            self.tab.feed.guard_wheel(kcb)
            kcb.bind("<<ComboboxSelected>>",
                     lambda e, rid=r["id"], v=kind_var, cb=kcb: (self.card.db.update_image(rid, kind=v.get()),
                                                                 cb.selection_clear()))
            ConfirmButton(line, command=lambda rid=r["id"]: self.card.delete_image(rid), text="Remove",
                          armed_text="Click again", bg=theme.PANEL2).pack(side="right")
        else:
            tk.Label(line, text=r["kind"].upper(), bg=theme.PANEL2, fg=theme.ACCENT,
                     font=(ui, 8, "bold")).pack(side="left")
            tk.Label(line, text="click to enlarge", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 8)).pack(side="right")
        return blk


class TradeCard(tk.Frame):
    TEXT_KEYS = ("trade_date", "trade_time", "instrument", "direction", "session", "entry", "sl", "tp",
                 "exit_price", "outcome", "result_r", "setup", "dxy_conf", "mistakes")

    def __init__(self, master, tab, row):
        super().__init__(master, bg=theme.PANEL, highlightthickness=2, highlightbackground=theme.BORDER)
        self.tab, self.db, self.id = tab, tab.db, row["id"]
        self.editing = row.get("status") == "draft"
        self.vars, self.widgets, self._job = {}, {}, None
        self.gallery = self.strip = self.status = self.finish_msg = None
        self.loading = True
        self._build(row)
        self.loading = False
        if self.editing:
            self.bind_active(self)
        self.apply_border()

    def destroy(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        super().destroy()

    # ------------------------------------------------------------ mode switching
    def _build(self, row):
        if self.editing:
            self._build_edit(row)
        else:
            self._build_view(row)

    def _rebuild(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        row = self.db.get_trade(self.id)
        if row is None:
            return
        for w in self.winfo_children():
            w.destroy()
        self.vars, self.widgets, self.gallery = {}, {}, None
        self.loading = True
        self._build(row)
        self.loading = False
        if self.editing:
            self.bind_active(self)
        self.apply_border()
        self.tab.refresh_stats()

    def start_edit(self):
        self.db.update_trade(self.id, {"status": "draft"})
        self.editing = True
        self.after(10, self._after_edit_start)

    def _after_edit_start(self):
        self._rebuild()
        self.tab.set_active(self)

    def finish(self):
        """Save, then switch to the compact read-only look."""
        if not self.save():
            if self.finish_msg is not None:
                self.finish_msg.configure(text="Fix the date / time format first (YYYY-MM-DD, HH:MM).",
                                          fg=theme.ORANGE)
            return
        self.db.update_trade(self.id, {"status": "done"})
        self.editing = False
        if self.tab.active is self:
            self.tab.active = None
        self.after(10, self._rebuild)

    def apply_border(self):
        if self.editing:
            color = theme.ACCENT if self.tab.active is self else "#2d4a7c"
        else:
            color = theme.BORDER
        self.configure(highlightbackground=color)

    # ============================================================ EDIT MODE
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

    def _build_edit(self, row):
        ui = theme.F["ui"]
        self.strip = tk.Frame(self, bg=theme.MUTED, width=6)
        self.strip.pack(side="left", fill="y")
        body = tk.Frame(self, bg=theme.PANEL)
        body.pack(side="left", fill="both", expand=True, padx=16, pady=14)

        # --- "editing" banner: the visual difference to a finished trade
        ban = tk.Frame(body, bg=theme.ACCENT_BG)
        ban.pack(fill="x", pady=(0, 12))
        tk.Label(ban, text="✎  EDITING", bg=theme.ACCENT_BG, fg=theme.ACCENT, font=(ui, 9, "bold"),
                 padx=10, pady=5).pack(side="left")
        tk.Label(ban, text="Everything autosaves. Press “Finish” at the bottom when this trade is complete.",
                 bg=theme.ACCENT_BG, fg=theme.MUTED, font=(ui, 9)).pack(side="left")

        # --- row 1: identity
        r1 = tk.Frame(body, bg=theme.PANEL)
        r1.pack(fill="x")
        tk.Label(r1, text=f"TRADE #{self.id}", bg=theme.PANEL, fg=theme.ACCENT,
                 font=(ui, 12, "bold")).pack(side="left", padx=(0, 16), anchor="s")
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
        self.gallery = Gallery(body, self, editable=True)
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

        # --- finish
        foot = tk.Frame(body, bg=theme.PANEL)
        foot.pack(fill="x", pady=(18, 0))
        ttk.Button(foot, text="Finish ✓", style="Accent.TButton", command=self.finish).pack(side="right")
        self.finish_msg = tk.Label(foot, text="", bg=theme.PANEL, fg=theme.ORANGE, font=(ui, 9))
        self.finish_msg.pack(side="right", padx=12)

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

    def _section_label(self, parent, text, top=16):
        tk.Label(parent, text=text, bg=theme.PANEL, fg=theme.ACCENT, font=(theme.F["ui"], 9, "bold"),
                 anchor="w").pack(fill="x", pady=(top, 5))

    def bind_active(self, widget):
        widget.bind("<FocusIn>", lambda e: self.tab.set_active(self), add="+")
        widget.bind("<Button-1>", lambda e: self.tab.set_active(self), add="+")
        for child in widget.winfo_children():
            self.bind_active(child)

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
        """Writes the card to the database. Returns True when date and time are valid."""
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if not self.editing or not self.vars:
            return True
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
        return date_ok and time_ok

    def _update_strip(self):
        self.strip.configure(bg=OUT_COLORS.get(self.vars["outcome"].get(), theme.MUTED))

    def _update_cl_label(self, verdict, score):
        if not verdict:
            self.cl_lbl.configure(text="no record", fg=theme.MUTED)
        else:
            pct = f"  ({score:.0f}%)" if score is not None else ""
            self.cl_lbl.configure(text=VERDICT_LABELS.get(verdict, verdict) + pct,
                                  fg=theme.VERDICT_COLORS.get(verdict, theme.MUTED))

    # ============================================================ DONE (read-only) MODE
    def _build_view(self, row):
        ui = theme.F["ui"]
        out = row.get("outcome") or "Open"
        color = OUT_COLORS.get(out, theme.MUTED)
        self.strip = tk.Frame(self, bg=color, width=6)
        self.strip.pack(side="left", fill="y")
        body = tk.Frame(self, bg=theme.PANEL)
        body.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        # --- header: identity on the left, result / checklist / actions on the right
        head = tk.Frame(body, bg=theme.PANEL)
        head.pack(fill="x")
        tk.Label(head, text=f"TRADE #{self.id}", bg=theme.PANEL, fg=theme.ACCENT,
                 font=(ui, 12, "bold")).pack(side="left", padx=(0, 14))
        meta = "   ·   ".join(x for x in (row.get("trade_date"), row.get("trade_time"), row.get("instrument"),
                                          row.get("session")) if x)
        tk.Label(head, text=meta, bg=theme.PANEL, fg=theme.FG, font=(ui, 11)).pack(side="left")
        d = row.get("direction")
        if d:
            _chip(head, d.upper(), theme.GREEN if d == "Long" else theme.RED).pack(side="left", padx=(12, 0))

        ConfirmButton(head, command=lambda: self.tab.delete_trade(self), text="Delete",
                      armed_text="Click again to delete", bg=theme.PANEL).pack(side="right")
        ttk.Button(head, text="✎ Edit", command=self.start_edit).pack(side="right", padx=(0, 8))
        res = (row.get("result_r") or "").strip()
        tk.Label(head, text=out.upper() + (f"   {res}" if res else ""), bg=theme.PANEL, fg=color,
                 font=(ui, 13, "bold")).pack(side="right", padx=(0, 18))
        verdict = row.get("cl_verdict")
        if verdict:
            score = row.get("cl_score")
            pct = f" ({score:.0f}%)" if score is not None else ""
            tk.Label(head, text="Checklist: " + VERDICT_LABELS.get(verdict, verdict) + pct, bg=theme.PANEL,
                     fg=theme.VERDICT_COLORS.get(verdict, theme.MUTED), font=(ui, 9, "bold")).pack(
                side="right", padx=(0, 18))

        # --- facts: only the fields that were filled in
        facts = [(label, (row.get(key) or "").strip()) for label, key in (
            ("Entry", "entry"), ("Stop", "sl"), ("Target", "tp"), ("Exit", "exit_price"),
            ("Setup", "setup"), ("DXY confirmation", "dxy_conf"), ("Mistakes", "mistakes"))]
        facts = [(label, value) for label, value in facts if value]
        if facts:
            grid = tk.Frame(body, bg=theme.PANEL)
            grid.pack(fill="x", pady=(10, 0))
            ncols = 4
            for c in range(ncols):
                grid.columnconfigure(c, weight=1, uniform="facts")
            for i, (label, value) in enumerate(facts):
                col = i % ncols
                tile = tk.Frame(grid, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
                tile.grid(row=i // ncols, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0), pady=(0, 8))
                tk.Label(tile, text=label.upper(), bg=theme.PANEL2,
                         fg=theme.ORANGE if label == "Mistakes" else theme.MUTED,
                         font=(ui, 8, "bold"), anchor="w").pack(fill="x", padx=10, pady=(6, 0))
                val = tk.Label(tile, text=value, bg=theme.PANEL2, fg=theme.FG, font=(ui, 11), anchor="w",
                               justify="left", wraplength=220)
                val.pack(fill="x", padx=10, pady=(1, 7))
                tile.bind("<Configure>", lambda e, l=val: l.configure(wraplength=max(100, e.width - 24)))

        # --- screenshots (read-only, three per row)
        images = self.db.list_images(self.id)
        if images:
            self.gallery = Gallery(body, self, editable=False)
            self.gallery.pack(fill="x", pady=(8, 0), anchor="w")
            self.gallery.set_rows(images)

        # --- reasoning + review
        for label, key in (("WHY I TOOK THIS TRADE", "why"), ("REVIEW — WHAT HAPPENED, WHAT I LEARNED", "review")):
            text = (row.get(key) or "").strip()
            if text:
                self._section_label(body, label, top=10)
                self._readonly_text(body, text)

    def _readonly_text(self, parent, text):
        t = tk.Text(parent, height=1, width=10, bg=theme.PANEL, fg=theme.FG, relief="flat", bd=0,
                    highlightthickness=0, wrap="word", font=(theme.F["ui"], 11), padx=0, pady=0, cursor="arrow",
                    selectbackground=theme.ACCENT, selectforeground="white", insertwidth=0)
        t.insert("1.0", text)
        bind_autosize(t, 1, 60)
        t.configure(state="disabled")
        t.bind("<Button-1>", lambda e: t.focus_set())          # so Ctrl+C works on selected text
        t.pack(fill="x")

    # ------------------------------------------------------------- images
    def render_gallery(self):
        if self.gallery is not None:
            self.gallery.set_rows(self.db.list_images(self.id))

    def open_viewer(self, idx):
        rows = self.db.list_images(self.id)
        items = [(IMAGES_DIR / r["filename"], r["kind"]) for r in rows]
        if items:
            ImageViewer(self.winfo_toplevel(), items, min(idx, len(items) - 1))

    def delete_image(self, image_id):
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
        if not self.editing:
            return False
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
        self._photos, self._pil = {}, {}
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
        # the card that receives Ctrl+V: the requested one, else the first trade still being edited
        target = (next((c for c in self.cards if c.id == select_id and c.editing), None)
                  or next((c for c in self.cards if c.editing), None))
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
        drafts = sum(1 for r in rows if r.get("status") == "draft")
        n = f"{len(rows)} trades" + (f" ({drafts} being edited)" if drafts else "")
        self.stats_lbl.configure(text=f"{n}   •   Win rate: {wr}   •   Total R: {total_r:+.2f}")

    def refresh_stats(self):
        self._update_stats(self._query())

    def set_active(self, card):
        if self.active is card:
            return
        self.active = card
        for c in self.cards:
            try:
                c.apply_border()
            except tk.TclError:
                pass

    def photo(self, row, w, h):
        """Screenshot as a w x h PhotoImage; PIL thumbnails and PhotoImages are cached (bounded)."""
        key = (row["id"], w, h)
        ph = self._photos.get(key)
        if ph is None:
            if len(self._photos) > 240:
                self._photos.clear()
            pil = self._pil.get(row["id"])
            if pil is None:
                if len(self._pil) > 80:
                    self._pil.clear()
                pil = self._pil[row["id"]] = thumb_image(row)
            ph = self._photos[key] = fit_photo(pil, w, h)
        return ph

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
        if not self.winfo_viewable() or not self.active or not self.active.editing:
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
