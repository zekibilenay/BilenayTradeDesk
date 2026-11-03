"""Pre-Trade Checklist tab.

Every item is a *requirement*: you write the requirement, then each day you explain in writing why it is
met and confirm it. Everything is edited directly on the page (no dialogs):
  - type under a section + Enter  -> adds a requirement
  - type in the bottom field      -> adds a section
  - drag the grip (⠿)             -> reorder requirements (also between sections) and sections
  - click ★                       -> mark a requirement as required
This tab is intentionally independent from the calendar.
"""
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from . import theme
from .checklist_model import (VERDICT_LABELS, coerce_answers, evaluate, load_template, new_id,
                              save_template)
from .widgets import ConfirmButton, PlaceholderEntry, ScrollFrame, bind_autosize

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
CONFIRMED_BORDER = "#245c3b"


class RequirementCard(tk.Frame):
    def __init__(self, master, tab, si, ii, item, answer):
        super().__init__(master, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
        self.tab, self.item, self.ans = tab, item, answer
        ui = theme.F["ui"]

        self.strip = tk.Frame(self, bg=theme.BORDER, width=5)
        self.strip.pack(side="left", fill="y")
        body = tk.Frame(self, bg=theme.PANEL2)
        body.pack(side="left", fill="both", expand=True, padx=(10, 12), pady=10)

        head = tk.Frame(body, bg=theme.PANEL2)
        head.pack(fill="x")
        self.handle = tk.Label(head, text="⠿", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 15), cursor="fleur")
        self.handle.pack(side="left", anchor="n", padx=(0, 8))
        self.handle.bind("<ButtonPress-1>", lambda e: tab.drag_start("item", si, ii, e))
        self.handle.bind("<B1-Motion>", tab.drag_motion)
        self.handle.bind("<ButtonRelease-1>", tab.drag_end)

        ConfirmButton(head, command=lambda: tab.delete_item(si, ii), bg=theme.PANEL2).pack(side="right", anchor="n")
        self.star = tk.Label(head, bg=theme.PANEL2, font=(ui, 14), cursor="hand2")
        self.star.pack(side="right", anchor="n", padx=(4, 4))
        self.star.bind("<Button-1>", lambda e: self._toggle_required())

        self.title = tk.Text(head, height=1, width=10)
        theme.style_text(self.title, (ui, 12, "bold"))
        self.title.configure(bg=theme.PANEL2, highlightbackground=theme.PANEL2, padx=2, pady=2)
        self.title.pack(side="left", fill="x", expand=True)
        self.title.insert("1.0", item["text"])
        bind_autosize(self.title, 1, 8)
        self.title.bind("<KeyRelease>", lambda e: tab.item_text_changed(item, self.title.get("1.0", "end-1c")), add="+")
        self.title.bind("<Return>", lambda e: (self.note.focus_set(), "break")[1])
        self.title.bind("<FocusOut>", self._title_focus_out)

        tk.Label(body, text="YOUR EXPLANATION", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 8, "bold"),
                 anchor="w").pack(fill="x", pady=(10, 3))
        self.note = tk.Text(body, height=3, width=10)
        theme.style_text(self.note, (ui, 10))
        self.note.pack(fill="x")
        self.note.insert("1.0", answer["note"])
        bind_autosize(self.note, 3, 20)
        self.note.bind("<KeyRelease>", self._note_changed, add="+")

        foot = tk.Frame(body, bg=theme.PANEL2)
        foot.pack(fill="x", pady=(8, 0))
        self.btn = ttk.Button(foot, command=self._toggle_confirm)
        self.btn.pack(side="left")
        self.msg = tk.Label(foot, text="", bg=theme.PANEL2, fg=theme.ORANGE, font=(ui, 9))
        self.msg.pack(side="left", padx=10)
        self.status = tk.Label(foot, bg=theme.PANEL2, font=(ui, 9, "bold"))
        self.status.pack(side="right")
        self.apply_state()

    # ----------------------------------------------------------- state
    def apply_state(self):
        confirmed = self.ans["confirmed"]
        required = self.item["required"]
        self.star.configure(text="★" if required else "☆", fg=theme.ORANGE if required else theme.MUTED)
        if confirmed:
            self.strip.configure(bg=theme.GREEN)
            self.configure(highlightbackground=CONFIRMED_BORDER)
            self.btn.configure(text="Undo", style="TButton")
            self.status.configure(text="✓ CONFIRMED", fg=theme.GREEN)
        else:
            self.strip.configure(bg=theme.ORANGE if required else theme.BORDER)
            self.configure(highlightbackground=theme.BORDER)
            self.btn.configure(text="Confirm ✓", style="Accent.TButton")
            self.status.configure(text="REQUIRED · PENDING" if required else "PENDING",
                                  fg=theme.ORANGE if required else theme.MUTED)

    def _toggle_required(self):
        self.item["required"] = not self.item["required"]
        self.apply_state()
        self.tab.structure_light_change()

    def _title_focus_out(self, _e=None):
        if not self.title.get("1.0", "end-1c").strip():          # never leave a requirement empty
            self.title.delete("1.0", "end")
            self.title.insert("1.0", self.item["text"])

    def _note_changed(self, _e=None):
        text = self.note.get("1.0", "end-1c")
        self.ans["note"] = text
        if self.ans["confirmed"] and not text.strip():           # explanation removed -> no longer confirmed
            self.ans["confirmed"] = False
            self.apply_state()
        self.tab.answers_changed()

    def _toggle_confirm(self):
        if not self.ans["confirmed"]:
            if not self.ans["note"].strip():
                self._flash("Write your explanation first.")
                return
            self.ans["confirmed"] = True
        else:
            self.ans["confirmed"] = False
        self.apply_state()
        self.tab.answers_changed(immediate=True)

    def _flash(self, text):
        self.note.configure(highlightbackground=theme.RED)
        self.msg.configure(text=text)
        self.note.focus_set()

        def reset():
            try:
                self.note.configure(highlightbackground=theme.BORDER)
                self.msg.configure(text="")
            except tk.TclError:
                pass
        self.after(1600, reset)


class ChecklistTab(ttk.Frame):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.template = load_template()
        self.day = date.today()
        self.answers = {}                 # item_id -> {"note": str, "confirmed": bool}
        self._sec_frames, self._sec_headers, self._item_cards = [], [], []
        self._count_lbls, self._add_entries = [], []
        self._slots, self._drag, self._drag_job, self._last_y = [], None, None, 0
        self._tpl_job = self._day_job = None
        self.indicator = None
        self._build()
        self.load_day(self.day)

    # ------------------------------------------------------------------ UI
    def _build(self):
        ui = theme.F["ui"]
        bar = ttk.Frame(self, padding=(12, 10, 12, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="◀", width=3, command=lambda: self._shift(-1)).pack(side="left")
        self.date_lbl = ttk.Label(bar, text="", style="Title.TLabel", width=34, anchor="center")
        self.date_lbl.pack(side="left", padx=8)
        ttk.Button(bar, text="▶", width=3, command=lambda: self._shift(1)).pack(side="left")
        ttk.Button(bar, text="Today", command=self._go_today).pack(side="left", padx=(10, 0))
        ConfirmButton(bar, command=self._reset_day, text="Reset day", armed_text="Click again to reset",
                      bg=theme.BG).pack(side="right")

        self.banner = tk.Frame(self, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
        self.banner.pack(fill="x", padx=12, pady=(0, 8))
        self.verdict_lbl = tk.Label(self.banner, text="", bg=theme.PANEL2, fg=theme.MUTED,
                                    font=(ui, 20, "bold"), padx=18, pady=10)
        self.verdict_lbl.pack(side="left")
        self.detail_lbl = tk.Label(self.banner, text="", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 10),
                                   justify="left")
        self.detail_lbl.pack(side="left", padx=10)
        thr = tk.Frame(self.banner, bg=theme.PANEL2)
        thr.pack(side="right", padx=14)
        tk.Label(thr, text="Clear ≥", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 9)).pack(side="left")
        self.sp_g = ttk.Spinbox(thr, from_=0, to=100, width=4, command=self._thresholds_changed)
        self.sp_g.pack(side="left", padx=(4, 12))
        tk.Label(thr, text="Caution ≥", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 9)).pack(side="left")
        self.sp_y = ttk.Spinbox(thr, from_=0, to=100, width=4, command=self._thresholds_changed)
        self.sp_y.pack(side="left", padx=(4, 0))
        tk.Label(thr, text="%", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 9)).pack(side="left", padx=(2, 0))
        self.sp_g.set(self.template["threshold_green"])
        self.sp_y.set(self.template["threshold_yellow"])
        for sp in (self.sp_g, self.sp_y):
            sp.bind("<Return>", self._thresholds_changed)
            sp.bind("<FocusOut>", self._thresholds_changed)

        self.scroll = ScrollFrame(self, bg=theme.PANEL)
        self.scroll.pack(fill="both", expand=True, padx=12)

        note_box = ttk.Frame(self, padding=(12, 8, 12, 12))
        note_box.pack(fill="x")
        ttk.Label(note_box, text="DAY NOTES", style="Muted.TLabel").pack(anchor="w")
        self.day_note = tk.Text(note_box, height=3)
        theme.style_text(self.day_note)
        self.day_note.pack(fill="x", pady=(4, 0))
        self.day_note.bind("<KeyRelease>", lambda e: self._save_day_soon())

    # ------------------------------------------------------------ rendering
    def _render(self, keep_scroll=True, focus=None):
        canvas = self.scroll.canvas
        y0 = canvas.yview()[0] if keep_scroll else 0.0
        inner = self.scroll.inner
        for w in inner.winfo_children():
            w.destroy()
        self._sec_frames, self._sec_headers, self._item_cards = [], [], []
        self._count_lbls, self._add_entries = [], []
        self.indicator = tk.Frame(inner, bg=theme.ACCENT, height=3)

        tk.Label(inner, text="Drag ⠿ to reorder  ·  ★ marks a requirement as required  ·  "
                             "type below a section and press Enter to add",
                 bg=theme.PANEL, fg=theme.MUTED, font=(theme.F["ui"], 9), anchor="w").pack(fill="x", padx=18, pady=(10, 0))

        for si, sec in enumerate(self.template["sections"]):
            self._build_section(si, sec)

        tk.Label(inner, text="NEW SECTION", bg=theme.PANEL, fg=theme.MUTED, font=(theme.F["ui"], 8, "bold"),
                 anchor="w").pack(fill="x", padx=18, pady=(22, 3))
        self.add_section_entry = PlaceholderEntry(inner, "+ Add a section — type a title and press Enter",
                                                  on_submit=self.add_section)
        self.add_section_entry.pack(fill="x", padx=16, pady=(0, 28), ipady=7)
        self.update_counts()

        def finish():
            try:
                canvas.yview_moveto(y0)
                if isinstance(focus, int) and 0 <= focus < len(self._add_entries):
                    self._add_entries[focus].focus_set()
                    self.scroll.see(self._add_entries[focus])
            except tk.TclError:
                pass
        self.after(40, finish)

    def _build_section(self, si, sec):
        ui = theme.F["ui"]
        sf = tk.Frame(self.scroll.inner, bg=theme.PANEL)
        sf.pack(fill="x", padx=16, pady=(16, 0))
        hdr = tk.Frame(sf, bg=theme.PANEL)
        hdr.pack(fill="x")

        handle = tk.Label(hdr, text="⠿", bg=theme.PANEL, fg=theme.MUTED, font=(ui, 15), cursor="fleur")
        handle.pack(side="left", padx=(0, 8))
        handle.bind("<ButtonPress-1>", lambda e: self.drag_start("section", si, None, e))
        handle.bind("<B1-Motion>", self.drag_motion)
        handle.bind("<ButtonRelease-1>", self.drag_end)

        ConfirmButton(hdr, command=lambda: self.delete_section(si), text="Delete section",
                      armed_text="Click again to delete", bg=theme.PANEL).pack(side="right")
        count = tk.Label(hdr, text="", bg=theme.PANEL, fg=theme.MUTED, font=(ui, 10))
        count.pack(side="right", padx=10)
        title = tk.Entry(hdr, bg=theme.PANEL, fg=theme.ACCENT, insertbackground=theme.FG, relief="flat",
                         highlightthickness=1, highlightbackground=theme.PANEL, highlightcolor=theme.ACCENT,
                         font=(ui, 13, "bold"))
        title.insert(0, sec["title"])
        title.pack(side="left", fill="x", expand=True)
        title.bind("<KeyRelease>", lambda e: self._section_title_changed(sec, title))
        title.bind("<FocusOut>", lambda e: self._section_title_focus_out(sec, title))
        tk.Frame(sf, bg=theme.BORDER, height=1).pack(fill="x", pady=(5, 6))

        items_frame = tk.Frame(sf, bg=theme.PANEL)
        items_frame.pack(fill="x")
        cards = []
        for ii, it in enumerate(sec["items"]):
            ans = self.answers.setdefault(it["id"], {"note": "", "confirmed": False})
            card = RequirementCard(items_frame, self, si, ii, it, ans)
            card.pack(fill="x", pady=4)
            cards.append(card)
        add = PlaceholderEntry(sf, "+ Add a requirement — type it and press Enter",
                               on_submit=lambda text, s=si: self.add_item(s, text))
        add.pack(fill="x", pady=(6, 0), ipady=6)

        self._sec_frames.append(sf)
        self._sec_headers.append(hdr)
        self._item_cards.append(cards)
        self._count_lbls.append(count)
        self._add_entries.append(add)

    # ------------------------------------------------------- template edits
    def add_item(self, si, text):
        self.template["sections"][si]["items"].append({"id": new_id(), "text": text, "required": False})
        self._save_template_soon()
        self._render(focus=si)
        self._update_banner()

    def add_section(self, title):
        self.template["sections"].append({"id": new_id(), "title": title, "items": []})
        self._save_template_soon()
        self._render(focus=len(self.template["sections"]) - 1)
        self._update_banner()

    def delete_item(self, si, ii):
        del self.template["sections"][si]["items"][ii]
        self._save_template_soon()
        self._render()
        self._update_banner()

    def delete_section(self, si):
        del self.template["sections"][si]
        self._save_template_soon()
        self._render()
        self._update_banner()

    def item_text_changed(self, item, text):
        t = text.strip()
        if t:
            item["text"] = t
            self._save_template_soon()

    def _section_title_changed(self, sec, entry):
        t = entry.get().strip()
        if t:
            sec["title"] = t
            self._save_template_soon()

    def _section_title_focus_out(self, sec, entry):
        if not entry.get().strip():
            entry.insert(0, sec["title"])

    def structure_light_change(self):
        """Required flag toggled: no re-render needed."""
        self._save_template_soon()
        self._update_banner()

    def _thresholds_changed(self, _e=None):
        try:
            g = max(0, min(100, int(self.sp_g.get())))
            y = max(0, min(100, int(self.sp_y.get())))
        except ValueError:
            self.sp_g.set(self.template["threshold_green"])
            self.sp_y.set(self.template["threshold_yellow"])
            return
        y = min(y, g)
        self.template["threshold_green"], self.template["threshold_yellow"] = g, y
        self.sp_g.set(g)
        self.sp_y.set(y)
        self._save_template_soon()
        self._update_banner()

    # -------------------------------------------------------------- drag & drop
    def drag_start(self, kind, a, b, event):
        self._drag = {"kind": kind, "si": a, "ii": b, "target": None}
        self._last_y = event.y_root
        self._compute_slots(kind)
        if kind == "item":
            try:
                self._item_cards[a][b].configure(highlightbackground=theme.ACCENT)
            except (IndexError, tk.TclError):
                pass
        self._drag_loop()

    def drag_motion(self, event):
        if self._drag:
            self._last_y = event.y_root
            self._drag_update(autoscroll=False)

    def _drag_loop(self):
        if not self._drag:
            return
        self._drag_update(autoscroll=True)
        self._drag_job = self.after(60, self._drag_loop)

    def _compute_slots(self, kind):
        base = self.scroll.inner.winfo_rooty()
        slots = []
        if kind == "item":
            for si, cards in enumerate(self._item_cards):
                hdr = self._sec_headers[si]
                if not cards:
                    slots.append((hdr.winfo_rooty() + hdr.winfo_height() - base + 10, si, 0))
                for ii, c in enumerate(cards):
                    slots.append((c.winfo_rooty() - base - 2, si, ii))
                if cards:
                    last = cards[-1]
                    slots.append((last.winfo_rooty() + last.winfo_height() - base + 3, si, len(cards)))
        else:
            for si, sf in enumerate(self._sec_frames):
                slots.append((sf.winfo_rooty() - base - 6, si))
            if self._sec_frames:
                last = self._sec_frames[-1]
                slots.append((last.winfo_rooty() + last.winfo_height() - base + 6, len(self._sec_frames)))
        self._slots = slots

    def _drag_update(self, autoscroll):
        if not self._drag or not self._slots:
            return
        canvas = self.scroll.canvas
        if autoscroll:
            top = canvas.winfo_rooty()
            bottom = top + canvas.winfo_height()
            if self._last_y < top + 50:
                canvas.yview_scroll(-2, "units")
            elif self._last_y > bottom - 50:
                canvas.yview_scroll(2, "units")
        y = self._last_y - self.scroll.inner.winfo_rooty()
        best = min(self._slots, key=lambda s: abs(s[0] - y))
        self._drag["target"] = best[1:]
        self.indicator.place(x=14, y=int(best[0]) - 1, relwidth=1.0, width=-28, height=3)
        self.indicator.lift()

    def drag_end(self, _event=None):
        d, self._drag = self._drag, None
        if self._drag_job:
            self.after_cancel(self._drag_job)
            self._drag_job = None
        try:
            self.indicator.place_forget()
        except tk.TclError:
            pass
        if not d or not d["target"]:
            self._render()
            return
        secs = self.template["sections"]
        if d["kind"] == "item":
            tsi, tii = d["target"]
            item = secs[d["si"]]["items"].pop(d["ii"])
            if tsi == d["si"] and d["ii"] < tii:
                tii -= 1
            secs[tsi]["items"].insert(tii, item)
        else:
            tsi = d["target"][0]
            sec = secs.pop(d["si"])
            if d["si"] < tsi:
                tsi -= 1
            secs.insert(tsi, sec)
        self._save_template_soon()
        self._render()
        self._update_banner()

    # ----------------------------------------------------------------- daily data
    def _date_key(self):
        return self.day.isoformat()

    def load_day(self, d):
        self.day = d
        rec = self.db.get_checklist_day(self._date_key())
        self.answers = coerce_answers(rec["answers"]) if rec else {}
        self.day_note.delete("1.0", "end")
        if rec and rec["note"]:
            self.day_note.insert("1.0", rec["note"])
        self._render(keep_scroll=False)
        suffix = "  •  TODAY" if d == date.today() else ""
        self.date_lbl.configure(text=f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}{suffix}")
        self._update_banner()

    def answers_changed(self, immediate=False):
        self.update_counts()
        self._update_banner()
        if immediate:
            self._save_day_now()
        else:
            self._save_day_soon()

    def update_counts(self):
        for si, sec in enumerate(self.template["sections"]):
            if si < len(self._count_lbls):
                done = sum(1 for it in sec["items"] if self.answers.get(it["id"], {}).get("confirmed"))
                self._count_lbls[si].configure(text=f"{done}/{len(sec['items'])} confirmed")

    def _update_banner(self):
        res = evaluate(self.template, self.answers)
        key = res["verdict"]
        color = theme.VERDICT_COLORS[key]
        self.verdict_lbl.configure(text=VERDICT_LABELS[key], fg=color)
        self.banner.configure(highlightbackground=color)
        parts = [f"Confirmed: {res['checked']}/{res['total']}  ({res['pct']:.0f}%)"]
        if res["req_total"]:
            parts.append(f"Required ★: {res['req_checked']}/{res['req_total']}")
            if not res["required_ok"]:
                parts.append(f"{res['req_total'] - res['req_checked']} required still pending")
        self.detail_lbl.configure(text="     ".join(parts))
        return res

    def _save_day_soon(self):
        if self._day_job:
            self.after_cancel(self._day_job)
        self._day_job = self.after(600, self._save_day_now)

    def _save_day_now(self):
        if self._day_job:
            try:
                self.after_cancel(self._day_job)
            except tk.TclError:
                pass
            self._day_job = None
        res = evaluate(self.template, self.answers)
        clean = {k: v for k, v in self.answers.items() if v["note"].strip() or v["confirmed"]}
        note = self.day_note.get("1.0", "end-1c").strip()
        if not clean and not note and not self.db.get_checklist_day(self._date_key()):
            return                                              # don't store empty days
        self.db.save_checklist_day(self._date_key(), clean, note, res["verdict"], res["pct"], res["required_ok"])

    def _save_template_soon(self):
        if self._tpl_job:
            self.after_cancel(self._tpl_job)
        self._tpl_job = self.after(500, self._save_template_now)

    def _save_template_now(self):
        if self._tpl_job:
            try:
                self.after_cancel(self._tpl_job)
            except tk.TclError:
                pass
            self._tpl_job = None
        save_template(self.template)

    # ---------------------------------------------------------------- navigation
    def _shift(self, delta):
        self._save_day_now()
        self.load_day(self.day + timedelta(days=delta))

    def _go_today(self):
        self._save_day_now()
        self.load_day(date.today())

    def _reset_day(self):
        self.db.delete_checklist_day(self._date_key())
        self.load_day(self.day)

    def save_current(self):
        self._save_day_now()
        self._save_template_now()
