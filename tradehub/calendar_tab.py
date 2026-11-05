"""Economic Calendar tab (ForexFactory weekly feed). Independent from checklist/journal."""
import json
import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta, timezone
from tkinter import ttk

from . import theme
from .calendar_data import fetch_feed, load_cache, parse_events, save_cache
from .paths import CALENDAR_NOTES_PATH, atomic_write_text

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CURRENCIES = ["ALL", "AUD", "CAD", "CHF", "CNY", "EUR", "GBP", "JPY", "NZD", "USD"]
IMPACTS = ["High", "Medium", "Low"]
REFRESH_MINUTES = 30
MIN_MANUAL_GAP_SEC = 120          # the ForexFactory feed answers frequent requests with HTTP 429
SOON_MINUTES = 30

TZ_OFFSETS = sorted({*range(-12, 15), -3.5, 3.5, 4.5, 5.5, 5.75, 6.5, 9.5})


def tz_label(offset):
    offset = float(offset)
    sign = "+" if offset >= 0 else "-"
    a = abs(offset)
    h = int(a)
    m = int(round((a - h) * 60))
    return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")


TZ_BY_LABEL = {tz_label(o): float(o) for o in TZ_OFFSETS}


class CalendarTab(ttk.Frame):
    def __init__(self, master, settings):
        super().__init__(master)
        self.settings = settings
        self.events, self.fetched_at = load_cache()
        self.source = "cache"
        self.view = settings.get("cal_view", "week")
        self._q = queue.Queue()
        self._fetching = False
        self._last_attempt = None
        self._last_minute = None
        self._status_extra = ""
        self._notes_job = None
        self._n_shown = 0
        self._build()
        self.render()
        self._notes_load()
        self._tick()

    # ------------------------------------------------------------ helpers
    def _offset(self):
        try:
            return float(self.settings.get("tz_offset", 3.0))
        except (TypeError, ValueError):
            return 3.0

    def _tz(self):
        return timezone(timedelta(hours=self._offset()))

    def _cache_is_stale(self):
        if not self.fetched_at:
            return True
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(self.fetched_at)
            return age > timedelta(minutes=REFRESH_MINUTES)
        except ValueError:
            return True

    # ----------------------------------------------------------------- UI
    def _build(self):
        ui = theme.F["ui"]
        bar = ttk.Frame(self, padding=(12, 10, 12, 4))
        bar.pack(fill="x")
        self.btn_today = ttk.Button(bar, text="Today", command=lambda: self._set_view("today"))
        self.btn_week = ttk.Button(bar, text="Full Week", command=lambda: self._set_view("week"))
        self.btn_today.pack(side="left")
        self.btn_week.pack(side="left", padx=(4, 0))
        self.next_lbl = ttk.Label(bar, text="", style="Muted.TLabel")
        self.next_lbl.pack(side="left", padx=18)

        # right side (packed right-to-left): clock, time zone picker, refresh
        self.clock_lbl = tk.Label(bar, text="--:--:--", bg=theme.BG, fg=theme.ACCENT, font=(theme.F["mono"], 12, "bold"),
                                  width=9, anchor="e")
        self.clock_lbl.pack(side="right")
        self.tz_var = tk.StringVar(value=tz_label(self._offset()))
        self.tz_cb = ttk.Combobox(bar, textvariable=self.tz_var, state="readonly", width=10,
                                  values=list(TZ_BY_LABEL.keys()), exportselection=False)
        self.tz_cb.pack(side="right", padx=(0, 14))
        self.tz_cb.bind("<<ComboboxSelected>>", self._on_tz)
        ttk.Label(bar, text="Time zone", style="Muted.TLabel").pack(side="right", padx=(0, 6))
        self.btn_refresh = ttk.Button(bar, text="⟳ Refresh", command=lambda: self.refresh(manual=True))
        self.btn_refresh.pack(side="right", padx=(0, 16))

        flt = ttk.Frame(self, padding=(12, 4, 12, 8))
        flt.pack(fill="x")
        ttk.Label(flt, text="Impact:", style="Muted.TLabel").pack(side="left")
        self.impact_vars = {}
        sel_imp = set(self.settings.get("cal_impacts"))
        for name in IMPACTS:
            v = tk.BooleanVar(value=name in sel_imp)
            self.impact_vars[name] = v
            ttk.Checkbutton(flt, text=name, variable=v, command=self._on_filter).pack(side="left", padx=(8, 0))
        ttk.Separator(flt, orient="vertical").pack(side="left", fill="y", padx=16)
        ttk.Label(flt, text="Currency:", style="Muted.TLabel").pack(side="left")
        ttk.Button(flt, text="Select all", command=lambda: self._set_all_ccy(True)).pack(side="left", padx=(8, 2))
        ttk.Button(flt, text="Clear", command=lambda: self._set_all_ccy(False)).pack(side="left", padx=(0, 8))
        self.ccy_vars = {}
        sel_ccy = set(self.settings.get("cal_currencies"))
        for c in CURRENCIES:
            v = tk.BooleanVar(value=c in sel_ccy)
            self.ccy_vars[c] = v
            ttk.Checkbutton(flt, text="General" if c == "ALL" else c, variable=v,
                            command=self._on_filter).pack(side="left", padx=(6, 0))

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12)
        self.paned = paned
        self.after(80, self._place_sash)
        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        cols = ("time", "ccy", "imp", "event", "forecast", "previous", "actual")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        spec = [("time", "Time", 140, "w"), ("ccy", "CCY", 66, "w"), ("imp", "Imp", 36, "center"),
                ("event", "Event", 190, "w"), ("forecast", "Forecast", 68, "e"),
                ("previous", "Previous", 68, "e"), ("actual", "Actual", 68, "e")]
        for key, text, width, anchor in spec:
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, minwidth=width if key != "event" else 120, anchor=anchor,
                             stretch=(key == "event"))
        # The scrollbar is packed BEFORE the tree: pack hands out space in packing order, so the other way round
        # the (wide) tree used up the whole pane and pushed the scrollbar out of view.
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        mono = (theme.F["mono"], 10)
        self.tree.tag_configure("day", background=theme.PANEL2, foreground=theme.FG, font=(ui, 10, "bold"))
        self.tree.tag_configure("today", background=theme.PANEL2, foreground=theme.ACCENT, font=(ui, 10, "bold"))
        colors = {"high": "#ff6b6b", "medium": "#f5b04c", "low": "#aab1bf"}
        dim = {"high": "#8a4a4a", "medium": "#8a7040", "low": "#5d6575"}
        for k in colors:
            self.tree.tag_configure(f"{k}_future", foreground=colors[k], font=mono)
            self.tree.tag_configure(f"{k}_past", foreground=dim[k], font=mono)
            self.tree.tag_configure(f"{k}_soon", foreground=colors[k], background="#2e2610", font=mono)

        nbar = ttk.Frame(right, padding=(8, 0, 0, 4))
        nbar.pack(fill="x")
        ttk.Label(nbar, text="NOTES", style="Title.TLabel").pack(side="left")
        self.notes_state = ttk.Label(nbar, text="", foreground=theme.GREEN)
        self.notes_state.pack(side="right")
        ttk.Button(nbar, text="I", width=3, command=lambda: self._toggle_tag("italic")).pack(side="right", padx=(0, 6))
        ttk.Button(nbar, text="B", width=3, command=lambda: self._toggle_tag("bold")).pack(side="right", padx=(0, 4))
        self.notes = tk.Text(right)
        theme.style_text(self.notes)
        self.notes.pack(fill="both", expand=True, padx=(8, 0))
        self.notes.tag_configure("bold", font=(ui, 10, "bold"))
        self.notes.tag_configure("italic", font=(ui, 10, "italic"))
        for seq, tag in (("<Control-b>", "bold"), ("<Control-B>", "bold"),
                         ("<Control-i>", "italic"), ("<Control-I>", "italic")):
            self.notes.bind(seq, lambda e=None, t=tag: self._toggle_tag(t))
        self.notes.bind("<KeyRelease>", self._notes_changed)

        self.status = ttk.Label(self, text="", style="Muted.TLabel", padding=(12, 6))
        self.status.pack(fill="x")
        self._update_view_buttons()

    def _place_sash(self):
        """Give the table ~62 % of the width, so all columns and the scrollbar fit."""
        try:
            w = self.paned.winfo_width()
            if w > 300:
                self.paned.sashpos(0, int(w * 0.62))
            else:
                self.after(100, self._place_sash)
        except tk.TclError:
            pass

    # ------------------------------------------------------- UI callbacks
    def _update_view_buttons(self):
        self.btn_today.configure(style="SegOn.TButton" if self.view == "today" else "Seg.TButton")
        self.btn_week.configure(style="SegOn.TButton" if self.view == "week" else "Seg.TButton")

    def _set_view(self, v):
        self.view = v
        self.settings.set("cal_view", v)
        self._update_view_buttons()
        self.render()

    def _set_all_ccy(self, on):
        for v in self.ccy_vars.values():
            v.set(on)
        self._on_filter()

    def _on_filter(self):
        self.settings.set("cal_impacts", [k for k, v in self.impact_vars.items() if v.get()], save=False)
        self.settings.set("cal_currencies", [k for k, v in self.ccy_vars.items() if v.get()])
        self.render()

    def _on_tz(self, _e=None):
        off = TZ_BY_LABEL.get(self.tz_var.get())
        if off is None:
            self.tz_var.set(tz_label(self._offset()))
            return
        self.settings.set("tz_offset", off)
        self.tz_cb.selection_clear()          # no leftover highlighted text in the box
        self.focus_set()                      # take focus away from the combobox
        self._update_clock()                  # clock follows the new zone immediately
        self.render()

    def _update_clock(self):
        now = datetime.now(timezone.utc).astimezone(self._tz())
        self.clock_lbl.configure(text=now.strftime("%H:%M:%S"))
        return now

    # ----------------------------------------------------------- render
    def render(self, scroll=True):
        tz = self._tz()
        now_utc = datetime.now(timezone.utc)
        today = now_utc.astimezone(tz).date()
        impacts = {k for k, v in self.impact_vars.items() if v.get()}
        ccys = {k for k, v in self.ccy_vars.items() if v.get()}
        y0 = self.tree.yview()[0]

        rows = []
        for ev in self.events:
            if ev["impact"] not in impacts or ev["country"] not in ccys:
                continue
            try:
                dt_utc = datetime.fromisoformat(ev["dt"])
            except ValueError:
                continue
            dt = dt_utc.astimezone(tz)
            if self.view == "today" and dt.date() != today:
                continue
            rows.append((dt_utc, dt, ev))

        self.tree.delete(*self.tree.get_children())
        last_date, next_iid, today_iid, next_ev, n = None, None, None, None, 0
        for dt_utc, dt, ev in rows:
            if dt.date() != last_date:
                last_date = dt.date()
                is_today = last_date == today
                head = f"{DAYS[dt.weekday()]}, {MONTHS[dt.month - 1]} {dt.day}"
                hid = self.tree.insert("", "end", values=(head, "", "", "• TODAY" if is_today else "", "", "", ""),
                                       tags=("today" if is_today else "day",))
                if is_today:
                    today_iid = hid
            minutes = (dt_utc - now_utc).total_seconds() / 60.0
            state = "past" if minutes < 0 else ("soon" if minutes <= SOON_MINUTES else "future")
            mark = "✓ " if state == "past" else "  "
            iid = self.tree.insert("", "end", values=(
                f"{mark}{dt.strftime('%H:%M')}", "GENERAL" if ev["country"] == "ALL" else ev["country"],
                ev["impact"][0], ev["title"], ev["forecast"] or "–", ev["previous"] or "–",
                ev["actual"] or "–"), tags=(f"{ev['impact'].lower()}_{state}",))
            n += 1
            if next_iid is None and minutes >= 0:
                next_iid, next_ev = iid, (ev, minutes)

        if scroll:
            target = next_iid or today_iid
            if target:
                self.tree.see(target)
        else:
            self.tree.yview_moveto(y0)

        if next_ev:
            ev, mins = next_ev
            when = f"in {int(mins)} min" if mins < 120 else f"in {mins / 60:.1f} h"
            self.next_lbl.configure(text=f"Next: {ev['country']} {ev['title']} — {when}")
        else:
            self.next_lbl.configure(text="")
        self._n_shown = n
        self._refresh_status()

    def _refresh_status(self):
        tz = self._tz()
        upd = "—"
        if self.fetched_at:
            try:
                upd = datetime.fromisoformat(self.fetched_at).astimezone(tz).strftime("%H:%M")
            except ValueError:
                upd = "?"
        parts = [f"{self._n_shown} events shown",
                 f"Last updated: {upd} ({tz_label(self._offset())})",
                 f"Source: {'ForexFactory' if self.source == 'ForexFactory' else 'cache'}",
                 f"Auto-refreshes every {REFRESH_MINUTES} min"]
        if self._status_extra:
            parts.append(self._status_extra)
        self.status.configure(text="  |  ".join(parts))

    def _tick(self):
        """Runs every second: keeps the clock live; once a minute re-evaluates event states."""
        try:
            now = self._update_clock()
            if now.minute != self._last_minute:
                self._last_minute = now.minute
                self.render(scroll=False)
                if (not self._fetching and self._cache_is_stale() and (
                        self._last_attempt is None or (datetime.now() - self._last_attempt).total_seconds() > 300)):
                    self.refresh(manual=False)
        finally:
            self.after(1000, self._tick)

    # ------------------------------------------------------------- fetch
    def refresh(self, manual=False):
        if self._fetching:
            return
        now = datetime.now()
        if manual and self._last_attempt and (now - self._last_attempt).total_seconds() < MIN_MANUAL_GAP_SEC:
            self._status_extra = "Refreshing too often — please wait 2 minutes"
            self._refresh_status()
            return
        self._last_attempt = now
        self._fetching = True
        self._status_extra = "Updating…"
        self._refresh_status()

        def work():
            try:
                self._q.put(("ok", parse_events(fetch_feed())))
            except Exception as exc:                      # network / HTTP 429 / format errors
                self._q.put(("err", str(exc)))

        threading.Thread(target=work, daemon=True).start()
        self.after(300, self._poll)

    def _poll(self):
        try:
            kind, payload = self._q.get_nowait()
        except queue.Empty:
            self.after(300, self._poll)
            return
        self._fetching = False
        if kind == "ok" and payload:
            self.events = payload
            self.fetched_at = save_cache(payload)
            self.source = "ForexFactory"
            self._status_extra = ""
            self.render(scroll=False)
        elif kind == "ok":
            self._status_extra = "Feed returned no events, using cache"
            self._refresh_status()
        else:
            self._status_extra = f"Update failed ({payload[:60]}), using cache"
            self._refresh_status()

    # -------------------------------------------------------------- notes
    def _toggle_tag(self, tag):
        try:
            s, e = self.notes.index("sel.first"), self.notes.index("sel.last")
        except tk.TclError:
            return "break"
        if tag in self.notes.tag_names(s):
            self.notes.tag_remove(tag, s, e)
        else:
            self.notes.tag_add(tag, s, e)
        self._notes_changed()
        return "break"

    def _notes_changed(self, _e=None):
        self.notes_state.configure(text="saving…", foreground=theme.MUTED)
        if self._notes_job:
            self.after_cancel(self._notes_job)
        self._notes_job = self.after(800, self._notes_save)

    def _notes_save(self):
        data = {"text": self.notes.get("1.0", "end-1c"), "tags": {}}
        for tag in ("bold", "italic"):
            r = self.notes.tag_ranges(tag)
            data["tags"][tag] = [[str(r[i]), str(r[i + 1])] for i in range(0, len(r), 2)]
        try:
            atomic_write_text(CALENDAR_NOTES_PATH, json.dumps(data, ensure_ascii=False))
            self.notes_state.configure(text="✓ saved", foreground=theme.GREEN)
        except OSError:
            self.notes_state.configure(text="could not save", foreground=theme.RED)

    def _notes_load(self):
        try:
            data = json.loads(CALENDAR_NOTES_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        self.notes.insert("1.0", data.get("text", ""))
        for tag, ranges in (data.get("tags") or {}).items():
            for a, b in ranges:
                try:
                    self.notes.tag_add(tag, a, b)
                except tk.TclError:
                    pass
        self.notes.edit_reset()

    def save_current(self):
        if self._notes_job:
            self.after_cancel(self._notes_job)
        self._notes_save()
