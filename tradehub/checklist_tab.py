"""Pre-Trade Checklist tab.

The page is built from sections. Every section has *options* (pick one, e.g. market phase: Expansion /
Retracement / ...) and every option has *steps* (what you do on the chart when it applies). Everything is
edited directly on the page:
  - "+ Choice" under a section      -> adds an option;  "+ Add step" inside an option -> adds a step
  - ✕ (click twice)                 -> deletes an option / step / section
  - "Select" on an option card      -> that option applies today
  - "Today's checklist" (bottom)    -> the steps of the options you selected; tick each one as you do it
This tab is intentionally independent from the calendar.
"""
import tkinter as tk
import tkinter.font as tkfont
from datetime import date, timedelta
from tkinter import ttk

from . import theme
from .checklist_model import (coerce_answers, coerce_choices, evaluate, load_template, new_id,
                              save_template, selected_steps)
from .widgets import ConfirmButton, ScrollFrame, bind_autosize

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
OPTION_COLUMNS = 4


class QuietAdd(tk.Frame):
    """A quiet "+ Something" link that turns into a one-line input when clicked (Enter adds, Esc cancels)."""

    def __init__(self, master, label, on_submit, bg=theme.PANEL):
        super().__init__(master, bg=bg)
        self.bg, self.on_submit, self.entry, self.hint = bg, on_submit, None, None
        self.btn = tk.Label(self, text=label, bg=bg, fg=theme.MUTED, font=(theme.F["ui"], 10), cursor="hand2",
                            padx=6, pady=3)
        self.btn.pack(side="left")
        self.btn.bind("<Button-1>", lambda e=None: self.open())
        self.btn.bind("<Enter>", lambda e=None: self.btn.configure(fg=theme.FG))
        self.btn.bind("<Leave>", lambda e=None: self.btn.configure(fg=theme.MUTED))

    def open(self):
        if self.entry is not None:
            self.entry.focus_set()
            return
        self.btn.pack_forget()
        field_bg = theme.PANEL if self.bg == theme.PANEL2 else theme.PANEL2
        self.entry = tk.Entry(self, bg=field_bg, fg=theme.FG, insertbackground=theme.FG, relief="flat",
                              highlightthickness=1, highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
                              font=(theme.F["ui"], 10), selectbackground=theme.ACCENT, selectforeground="white")
        self.entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.hint = tk.Label(self, text="Enter to add · Esc to cancel", bg=self.bg, fg=theme.MUTED,
                             font=(theme.F["ui"], 9))
        self.hint.pack(side="left", padx=(8, 0))
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<Escape>", lambda e=None: self.close())
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.focus_set()

    def close(self):
        if self.entry is None:
            return
        try:
            self.entry.destroy()
            self.hint.destroy()
            self.btn.pack(side="left")
        except tk.TclError:
            pass
        self.entry = self.hint = None

    def _focus_out(self, _e=None):
        try:
            if self.entry is not None and not self.entry.get().strip():
                self.close()
        except tk.TclError:
            pass

    def _submit(self, _e=None):
        text = self.entry.get().strip() if self.entry is not None else ""
        if text:
            self.on_submit(text)
        else:
            self.close()


class OptionCard(tk.Frame):
    """One option: a name, its steps (add / edit / delete) and a Select button."""

    def __init__(self, master, tab, si, oi, option, selected):
        super().__init__(master, bg=theme.PANEL2, highlightthickness=2, highlightbackground=theme.BORDER)
        self.tab, self.option = tab, option
        ui = theme.F["ui"]
        body = tk.Frame(self, bg=theme.PANEL2)
        body.pack(fill="both", expand=True, padx=12, pady=10)
        self.btn = ttk.Button(body, command=lambda: tab.select_option(si, oi))
        self.btn.pack(side="bottom", anchor="w", pady=(10, 0))

        head = tk.Frame(body, bg=theme.PANEL2)
        head.pack(fill="x")
        ConfirmButton(head, command=lambda: tab.delete_option(si, oi), bg=theme.PANEL2).pack(side="right")
        self.dot = tk.Label(head, text="○", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 14))
        self.dot.pack(side="left", padx=(0, 6))
        self.title = tk.Entry(head, bg=theme.PANEL2, fg=theme.FG, insertbackground=theme.FG, relief="flat",
                              highlightthickness=1, highlightbackground=theme.PANEL2,
                              highlightcolor=theme.ACCENT, font=(ui, 12, "bold"),
                              selectbackground=theme.ACCENT, selectforeground="white")
        self.title.insert(0, option["title"])
        self.title.pack(side="left", fill="x", expand=True)
        self.title.bind("<KeyRelease>", lambda e=None: tab.option_title_changed(option, self.title.get()))
        self.title.bind("<FocusOut>", self._title_focus_out)

        tk.Label(body, text="STEPS", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 8, "bold"),
                 anchor="w").pack(fill="x", pady=(8, 3))
        self.adder = QuietAdd(body, "+ Add step", lambda text: tab.add_step(si, oi, text), bg=theme.PANEL2)
        self.adder.pack(side="bottom", fill="x")
        steps = tk.Frame(body, bg=theme.PANEL2)
        steps.pack(fill="x")
        for k, st in enumerate(option["steps"]):
            self._step_row(steps, si, oi, k, st)
        self.apply_state(selected)

    def _step_row(self, parent, si, oi, k, step):
        ui = theme.F["ui"]
        row = tk.Frame(parent, bg=theme.PANEL2)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=f"{k + 1}.", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 10), width=2,
                 anchor="ne").pack(side="left", anchor="n", pady=(5, 0))
        ConfirmButton(row, command=lambda: self.tab.delete_step(si, oi, k), bg=theme.PANEL2).pack(
            side="right", anchor="n")
        txt = tk.Text(row, height=1, width=10)
        theme.style_text(txt, (ui, 10))
        txt.configure(padx=6, pady=3)
        txt.pack(side="left", fill="x", expand=True)
        txt.insert("1.0", step["text"])
        bind_autosize(txt, 1, 6)
        txt.bind("<KeyRelease>", lambda e=None: self.tab.step_text_changed(step, txt.get("1.0", "end-1c")), add="+")
        txt.bind("<Return>", lambda e=None: (self.adder.open(), "break")[1])     # Enter: next step, no newline
        txt.bind("<FocusOut>", lambda e=None: self._step_focus_out(step, txt))

    @staticmethod
    def _step_focus_out(step, txt):
        if not txt.get("1.0", "end-1c").strip():             # never leave a step empty
            txt.delete("1.0", "end")
            txt.insert("1.0", step["text"])

    def apply_state(self, selected):
        if selected:
            self.configure(highlightbackground=theme.ACCENT)
            self.dot.configure(text="●", fg=theme.ACCENT)
            self.title.configure(fg=theme.ACCENT)
            self.btn.configure(text="Selected ✓", style="Accent.TButton")
        else:
            self.configure(highlightbackground=theme.BORDER)
            self.dot.configure(text="○", fg=theme.MUTED)
            self.title.configure(fg=theme.FG)
            self.btn.configure(text="Select", style="Pick.TButton")

    def _title_focus_out(self, _e=None):
        if not self.title.get().strip():                          # never leave an option without a name
            self.title.delete(0, "end")
            self.title.insert(0, self.option["title"])


class ChecklistTab(ttk.Frame):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.template = load_template()
        self.day = date.today()
        self.answers = {}                 # step_id -> {"note": "", "confirmed": bool}
        self.choices = {}                 # section_id -> option_id (the option picked for the day)
        self._opt_cards, self._sec_adders = [], []
        self._tpl_job = self._day_job = None
        self._today_box = None
        self._f_done = None
        self._build()
        self.load_day(self.day)

    # ------------------------------------------------------------------ UI
    def _build(self):
        bar = ttk.Frame(self, padding=(12, 10, 12, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="◀", width=3, command=lambda: self._shift(-1)).pack(side="left")
        self.date_lbl = ttk.Label(bar, text="", style="Title.TLabel", width=34, anchor="center")
        self.date_lbl.pack(side="left", padx=8)
        ttk.Button(bar, text="▶", width=3, command=lambda: self._shift(1)).pack(side="left")
        ttk.Button(bar, text="Today", command=self._go_today).pack(side="left", padx=(10, 0))
        ConfirmButton(bar, command=self._reset_day, text="Reset day", armed_text="Click again to reset",
                      bg=theme.BG).pack(side="right")
        self.scroll = ScrollFrame(self, bg=theme.PANEL)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ------------------------------------------------------------ rendering
    def _render(self, keep_scroll=True, focus=None):
        canvas = self.scroll.canvas
        y0 = canvas.yview()[0] if keep_scroll else 0.0
        inner = self.scroll.inner
        for w in inner.winfo_children():
            w.destroy()
        self._opt_cards, self._sec_adders, self._today_box = [], [], None

        tk.Label(inner, text="Pick one option per section. The steps of the options you pick appear in "
                             "“Today's checklist” at the bottom: tick each one as you do it.",
                 bg=theme.PANEL, fg=theme.MUTED, font=(theme.F["ui"], 9), anchor="w").pack(
            fill="x", padx=18, pady=(10, 0))
        for si, sec in enumerate(self.template["sections"]):
            self._build_section(si, sec)
        QuietAdd(inner, "+ New section", self.add_section).pack(fill="x", padx=16, pady=(14, 6), anchor="w")

        self._today_box = tk.Frame(inner, bg=theme.PANEL2, highlightthickness=1, highlightbackground=theme.BORDER)
        self._today_box.pack(fill="x", padx=16, pady=(8, 28))
        self._fill_today()

        def finish():
            try:
                canvas.yview_moveto(y0)
                if focus:
                    kind, si = focus[0], focus[1]
                    if kind == "choice_add":
                        w = self._sec_adders[si]
                    elif kind == "step_add":
                        w = self._opt_cards[si][focus[2]].adder
                    else:                                                      # "option_title"
                        w = self._opt_cards[si][focus[2]]
                    if kind == "option_title":
                        w.title.focus_set()
                        w.title.select_range(0, "end")
                    else:
                        w.open()
                    self.scroll.see(w)
            except (tk.TclError, IndexError):
                pass
        self.after(40, finish)

    def _build_section(self, si, sec):
        ui = theme.F["ui"]
        sf = tk.Frame(self.scroll.inner, bg=theme.PANEL)
        sf.pack(fill="x", padx=16, pady=(16, 0))
        hdr = tk.Frame(sf, bg=theme.PANEL)
        hdr.pack(fill="x")
        ConfirmButton(hdr, command=lambda: self.delete_section(si), text="Delete section",
                      armed_text="Click again to delete", bg=theme.PANEL).pack(side="right")
        for text, delta in (("▼", 1), ("▲", -1)):                   # move the section down / up
            lbl = tk.Label(hdr, text=text, bg=theme.PANEL, fg=theme.MUTED, font=(ui, 10), cursor="hand2", padx=5)
            lbl.pack(side="right")
            lbl.bind("<Button-1>", lambda e=None, d=delta: self.move_section(si, d))
        title = tk.Entry(hdr, bg=theme.PANEL, fg=theme.ACCENT, insertbackground=theme.FG, relief="flat",
                         highlightthickness=1, highlightbackground=theme.PANEL, highlightcolor=theme.ACCENT,
                         font=(ui, 13, "bold"), selectbackground=theme.ACCENT, selectforeground="white")
        title.insert(0, sec["title"])
        title.pack(side="left", fill="x", expand=True)
        title.bind("<KeyRelease>", lambda e=None: self._section_title_changed(sec, title))
        title.bind("<FocusOut>", lambda e=None: self._section_title_focus_out(sec, title))
        tk.Frame(sf, bg=theme.BORDER, height=1).pack(fill="x", pady=(5, 8))

        cards = []
        chosen = self.choices.get(sec["id"])
        if sec["options"]:
            grid = tk.Frame(sf, bg=theme.PANEL)
            grid.pack(fill="x")
            for c in range(OPTION_COLUMNS):
                grid.columnconfigure(c, weight=1, uniform=f"opt{si}")
            for oi, opt in enumerate(sec["options"]):
                card = OptionCard(grid, self, si, oi, opt, opt["id"] == chosen)
                col = oi % OPTION_COLUMNS
                card.grid(row=oi // OPTION_COLUMNS, column=col, sticky="nsew",
                          padx=(0 if col == 0 else 8, 0), pady=(0, 8))
                cards.append(card)
        adder = QuietAdd(sf, "+ Choice", lambda text, s=si: self.add_option(s, text))
        adder.pack(fill="x", pady=(0, 2), anchor="w")
        self._opt_cards.append(cards)
        self._sec_adders.append(adder)

    # --------------------------------------------------- "Today's checklist" (bottom)
    def _fill_today(self):
        box = self._today_box
        if box is None:
            return
        try:
            for w in box.winfo_children():
                w.destroy()
        except tk.TclError:
            return
        ui = theme.F["ui"]
        if self._f_done is None:
            self._f_done = tkfont.Font(family=ui, size=11, overstrike=True)
        steps = selected_steps(self.template, self.choices)
        done = sum(1 for _s, _o, st in steps if self.answers.get(st["id"], {}).get("confirmed"))

        inner = tk.Frame(box, bg=theme.PANEL2)
        inner.pack(fill="x", padx=16, pady=14)
        head = tk.Frame(inner, bg=theme.PANEL2)
        head.pack(fill="x")
        tk.Label(head, text="Today's checklist", bg=theme.PANEL2, fg=theme.FG, font=(ui, 13, "bold")).pack(side="left")
        tk.Label(head, text=f"{done} of {len(steps)} done" if steps else "", bg=theme.PANEL2, fg=theme.MUTED,
                 font=(ui, 10)).pack(side="right")
        track = tk.Frame(inner, bg=theme.BORDER, height=5)
        track.pack(fill="x", pady=(8, 6))
        if steps:
            tk.Frame(track, bg=theme.GREEN if done == len(steps) else theme.ACCENT, height=5).place(
                x=0, y=0, relheight=1.0, relwidth=done / len(steps))
        if not steps:
            tk.Label(inner, text="Select an option in a section to see its steps here.", bg=theme.PANEL2,
                     fg=theme.MUTED, font=(ui, 10), anchor="w").pack(fill="x", pady=(6, 0))
        last = None
        for sec in self.template["sections"]:
            oid = self.choices.get(sec["id"])
            opt = next((o for o in sec["options"] if o["id"] == oid), None)
            if opt is None:
                continue
            g = tk.Frame(inner, bg=theme.PANEL2)
            g.pack(fill="x", pady=(10, 2))
            tk.Label(g, text=f"{sec['title']}  ·  ", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 9)).pack(side="left")
            tk.Label(g, text=opt["title"], bg=theme.PANEL2, fg=theme.ACCENT, font=(ui, 9, "bold")).pack(side="left")
            if not opt["steps"]:
                tk.Label(inner, text="No steps yet. Add some in the option card above.", bg=theme.PANEL2,
                         fg=theme.MUTED, font=(ui, 10), anchor="w").pack(fill="x")
            for st in opt["steps"]:
                last = self._step_check_row(inner, st)

    def _step_check_row(self, parent, step):
        ui = theme.F["ui"]
        ticked = bool(self.answers.get(step["id"], {}).get("confirmed"))
        row = tk.Frame(parent, bg=theme.PANEL2, cursor="hand2")
        row.pack(fill="x")
        mark = tk.Label(row, text="☑" if ticked else "☐", bg=theme.PANEL2, font=(ui, 14),
                        fg=theme.GREEN if ticked else theme.MUTED, cursor="hand2")
        mark.pack(side="left", padx=(0, 10), anchor="n")
        txt = tk.Label(row, text=step["text"], bg=theme.PANEL2, fg=theme.MUTED if ticked else theme.FG,
                       font=self._f_done if ticked else (ui, 11), anchor="w", justify="left", wraplength=600,
                       cursor="hand2")
        txt.pack(side="left", fill="x", expand=True, pady=4)
        tk.Frame(parent, bg=theme.BORDER, height=1).pack(fill="x")
        for w in (row, mark, txt):
            w.bind("<Button-1>", lambda e=None, sid=step["id"]: self.toggle_step(sid))
        row.bind("<Configure>", lambda e=None: txt.configure(wraplength=max(120, row.winfo_width() - 50)))
        return row

    def toggle_step(self, step_id):
        a = self.answers.setdefault(step_id, {"note": "", "confirmed": False})
        a["confirmed"] = not a["confirmed"]
        self._fill_today()
        self._save_day_soon()

    # ------------------------------------------------------- template edits
    def add_option(self, si, title):
        opts = self.template["sections"][si]["options"]
        opts.append({"id": new_id(), "title": title, "steps": []})
        self._save_template_soon()
        self._render(focus=("step_add", si, len(opts) - 1))

    def delete_option(self, si, oi):
        sec = self.template["sections"][si]
        opt = sec["options"].pop(oi)
        if self.choices.get(sec["id"]) == opt["id"]:
            del self.choices[sec["id"]]
        for st in opt["steps"]:
            self.answers.pop(st["id"], None)
        self._save_day_now()
        self._save_template_soon()
        self._render()

    def option_title_changed(self, option, text):
        t = text.strip()
        if t:
            option["title"] = t
            self._save_template_soon()
            self._fill_today()

    def add_step(self, si, oi, text):
        steps = self.template["sections"][si]["options"][oi]["steps"]
        steps.append({"id": new_id(), "text": text.replace("\n", " ").strip()})
        self._save_template_soon()
        self._render(focus=("step_add", si, oi))                 # keep the input open: add the next step right away

    def delete_step(self, si, oi, k):
        steps = self.template["sections"][si]["options"][oi]["steps"]
        st = steps.pop(k)
        self.answers.pop(st["id"], None)
        self._save_day_now()
        self._save_template_soon()
        self._render()

    def step_text_changed(self, step, text):
        t = text.replace("\n", " ").strip()
        if t:
            step["text"] = t
            self._save_template_soon()
            self._fill_today()

    def select_option(self, si, oi):
        """Pick (or un-pick) today's option for a section. Updates the cards in place: no re-render."""
        sec = self.template["sections"][si]
        opt = sec["options"][oi]
        if self.choices.get(sec["id"]) == opt["id"]:
            del self.choices[sec["id"]]
        else:
            self.choices[sec["id"]] = opt["id"]
        chosen = self.choices.get(sec["id"])
        for card, o in zip(self._opt_cards[si], sec["options"]):
            card.apply_state(o["id"] == chosen)
        self._fill_today()
        self._save_day_now()

    def add_section(self, title):
        self.template["sections"].append({"id": new_id(), "title": title, "options": []})
        self._save_template_soon()
        self._render(focus=("choice_add", len(self.template["sections"]) - 1))

    def delete_section(self, si):
        sec = self.template["sections"].pop(si)
        self.choices.pop(sec["id"], None)
        self._save_day_now()
        self._save_template_soon()
        self._render()

    def move_section(self, si, delta):
        secs = self.template["sections"]
        j = si + delta
        if 0 <= j < len(secs):
            secs[si], secs[j] = secs[j], secs[si]
            self._save_template_soon()
            self._render()

    def _section_title_changed(self, sec, entry):
        t = entry.get().strip()
        if t:
            sec["title"] = t
            self._save_template_soon()
            self._fill_today()

    def _section_title_focus_out(self, sec, entry):
        if not entry.get().strip():
            entry.insert(0, sec["title"])

    # ----------------------------------------------------------------- daily data
    def _date_key(self):
        return self.day.isoformat()

    def load_day(self, d):
        self.day = d
        rec = self.db.get_checklist_day(self._date_key())
        self.answers = coerce_answers(rec["answers"]) if rec else {}
        self.choices = coerce_choices(rec.get("choices"), self.template) if rec else {}
        self._render(keep_scroll=False)
        suffix = "  •  TODAY" if d == date.today() else ""
        self.date_lbl.configure(text=f"{DAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}{suffix}")

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
        choices = coerce_choices(self.choices, self.template)
        res = evaluate(self.template, self.answers, choices)
        step_ids = {st["id"] for sec in self.template["sections"] for o in sec["options"] for st in o["steps"]}
        clean = {k: v for k, v in self.answers.items() if v["confirmed"] and k in step_ids}
        if not clean and not choices and not self.db.get_checklist_day(self._date_key()):
            return                                              # don't store empty days
        self.db.save_checklist_day(self._date_key(), clean, choices, res["verdict"], res["pct"], True)

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
