"""Shared widgets: scrollable page, placeholder entry, 2-step delete button, auto-height text."""
import tkinter as tk
from tkinter import ttk

from . import theme
from .platform_utils import wheel_notches


class ScrollFrame(ttk.Frame):
    """Vertically scrollable area. Put content into `.inner`."""

    def __init__(self, master, bg=None, wheel_px=None, **kw):
        """wheel_px: pixels one mouse-wheel notch scrolls. None keeps Tk's default (a big jump)."""
        super().__init__(master, **kw)
        bg = bg or theme.PANEL
        self.wheel_px, self._wheel_acc = wheel_px, 0.0
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        if wheel_px:
            self.canvas.configure(yscrollincrement=1)          # one "unit" = one pixel
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", self._on_wheel, add="+")
        self.bind_all("<Button-5>", self._on_wheel, add="+")
        self.on_width = None

    def keep_scroll(self, rebuild):
        """Run rebuild() (which destroys / recreates widgets inside `.inner`) without the page jumping."""
        top = self.canvas.canvasy(0)
        rebuild()
        self.inner.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)
            height = bbox[3] - bbox[1]
            if height > 0:
                self.canvas.yview_moveto(max(0.0, top - bbox[1]) / height)

    def _on_inner(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        if self.on_width:
            self.on_width(e.width)

    def _on_wheel(self, e, force=False):
        try:
            if not self.winfo_viewable():
                return
            w = e.widget
            if not force:
                if isinstance(w, (ttk.Treeview, tk.Listbox)):
                    return
                if isinstance(w, tk.Text) and tuple(w.yview()) != (0.0, 1.0):
                    return                    # the text box has its own scrolling
            x, y = self.winfo_pointerxy()
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            if not (rx <= x < rx + self.winfo_width() and ry <= y < ry + self.winfo_height()):
                return
            if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
                return
            num = getattr(e, "num", None)
            if self.wheel_px:
                # smooth, pixel-exact: a notch is 120 delta units, touchpads send smaller fractions
                notches = wheel_notches(num, getattr(e, "delta", 0))
                self._wheel_acc += -notches * self.wheel_px
                move = int(self._wheel_acc)
                self._wheel_acc -= move
                if move:
                    self.canvas.yview_scroll(move, "units")
                return
            if num == 4:
                step = -3
            elif num == 5:
                step = 3
            else:
                step = -3 if e.delta > 0 else 3
            self.canvas.yview_scroll(step, "units")
        except (tk.TclError, TypeError):
            pass

    def guard_wheel(self, widget):
        """Stop a widget (e.g. Combobox) from changing its value on wheel; scroll the page instead."""
        def handler(e):
            self._on_wheel(e, force=True)
            return "break"
        widget.bind("<MouseWheel>", handler)
        widget.bind("<Button-4>", handler)
        widget.bind("<Button-5>", handler)

    def scroll_top(self):
        self.canvas.yview_moveto(0)

    def see(self, widget, margin=60):
        """Scroll just enough so `widget` is fully visible."""
        try:
            self.update_idletasks()
            total = max(1, self.inner.winfo_height())
            view_h = self.canvas.winfo_height()
            top = self.canvas.yview()[0] * total
            y = widget.winfo_rooty() - self.inner.winfo_rooty()
            h = widget.winfo_height()
            if y < top + margin:
                new = y - margin
            elif y + h > top + view_h - margin:
                new = y + h - view_h + margin
            else:
                return
            self.canvas.yview_moveto(max(0.0, new) / total)
        except tk.TclError:
            pass


class PlaceholderEntry(tk.Entry):
    """Entry with grey hint text. Enter submits (calls on_submit(text))."""

    def __init__(self, master, placeholder, on_submit=None, bg=None, **kw):
        super().__init__(master, bg=bg or theme.PANEL2, fg=theme.MUTED, insertbackground=theme.FG, relief="flat",
                         highlightthickness=1, highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
                         font=(theme.F["ui"], 11), **kw)
        self.placeholder = placeholder
        self.on_submit = on_submit
        self._ph = False
        self._show_placeholder()
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Return>", self._submit)

    def _show_placeholder(self):
        self.delete(0, "end")
        self.insert(0, self.placeholder)
        self.configure(fg=theme.MUTED)
        self._ph = True

    def _focus_in(self, _e=None):
        if self._ph:
            self.delete(0, "end")
            self.configure(fg=theme.FG)
            self._ph = False

    def _focus_out(self, _e=None):
        if not tk.Entry.get(self).strip():
            self._show_placeholder()

    def value(self):
        return "" if self._ph else tk.Entry.get(self).strip()

    def _submit(self, _e=None):
        text = self.value()
        if text and self.on_submit:
            self.on_submit(text)          # the caller may rebuild the page; don't touch self afterwards
        return "break"


class ConfirmButton(tk.Label):
    """Inline two-step button: first click arms it, a second click within 3 s runs the command."""

    def __init__(self, master, command, text="✕", armed_text="Delete?", bg=None, **kw):
        bg = bg or theme.PANEL2
        super().__init__(master, text=text, bg=bg, fg=theme.MUTED, cursor="hand2",
                         font=(theme.F["ui"], 10), padx=8, pady=2, **kw)
        self._cmd, self._text, self._armed_text, self._bg = command, text, armed_text, bg
        self._armed, self._job = False, None
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e=None: None if self._armed else self.configure(fg=theme.RED))
        self.bind("<Leave>", lambda e=None: None if self._armed else self.configure(fg=theme.MUTED))

    def _click(self, _e=None):
        if self._armed:
            self._disarm()
            self._cmd()
        else:
            self._armed = True
            self.configure(text=self._armed_text, fg="#ffffff", bg=theme.RED_BTN)
            self._job = self.after(3000, self._disarm)

    def _disarm(self):
        try:
            if self._job:
                self.after_cancel(self._job)
            self._job = None
            self._armed = False
            self.configure(text=self._text, fg=theme.MUTED, bg=self._bg)
        except tk.TclError:
            pass


def autosize_text(txt, min_lines=1, max_lines=30):
    """Make a Text widget exactly as tall as its content (wrapped lines included)."""
    try:
        narrow = txt.winfo_width() < 40
    except tk.TclError:                    # widget already destroyed (delayed call)
        return
    if narrow:
        return
    try:
        res = txt.count("1.0", "end", "displaylines")
        n = res[0] if isinstance(res, (tuple, list)) else res
        n = int(n or 1)
    except Exception:
        try:
            n = txt.get("1.0", "end-1c").count("\n") + 1
        except tk.TclError:
            return
    n = max(min_lines, min(max_lines, n))
    try:
        if int(txt.cget("height")) != n:
            txt.configure(height=n)
    except tk.TclError:
        pass


def bind_autosize(txt, min_lines=1, max_lines=30):
    txt.configure(height=min_lines)
    txt.bind("<Configure>", lambda e=None: autosize_text(txt, min_lines, max_lines), add="+")
    txt.bind("<KeyRelease>", lambda e=None: autosize_text(txt, min_lines, max_lines), add="+")
    txt.after(50, lambda: autosize_text(txt, min_lines, max_lines))


class SuggestBox(tk.Frame):
    """Text box with a drop-down of earlier values. Every value in the list has a ✕ on its right: it removes the value
    from the suggestions (get_values / on_delete are supplied by the caller; the box never touches saved data).
    You can always type something new: pressing Enter in the box closes the list and calls on_enter(value), which the
    caller uses to save the value for good. Clicking a value fills the box and calls on_pick(value)."""

    ROW_H, MAX_ROWS = 28, 8
    _active = None                    # the box whose list is open (only one at a time)
    _hooked = False

    def __init__(self, master, textvariable, get_values, on_delete=None, on_pick=None, width=12, bg=None,
                 on_enter=None):
        bg = bg or theme.PANEL
        super().__init__(master, bg=bg)
        self.var, self.get_values, self.on_delete, self.on_pick = textvariable, get_values, on_delete, on_pick
        self.on_enter = on_enter
        self._pop = None
        self.typed = False                # True once text was typed by hand (not picked from the list)
        self.entry = ttk.Entry(self, textvariable=textvariable, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        self.arrow = tk.Label(self, text="▾", bg=theme.PANEL2, fg=theme.MUTED, cursor="hand2", padx=7,
                              font=(theme.F["ui"], 10))
        self.arrow.pack(side="left", fill="y", padx=(2, 0))
        self.arrow.bind("<Button-1>", lambda e=None: self.toggle())
        self.arrow.bind("<Enter>", lambda e=None: self.arrow.configure(fg=theme.FG))
        self.arrow.bind("<Leave>", lambda e=None: self.arrow.configure(fg=theme.MUTED))
        self.entry.bind("<Key>", self._on_key, add="+")
        self.entry.bind("<Down>", lambda e=None: (self.open(), "break")[1])
        self.entry.bind("<Escape>", lambda e=None: self.close(), add="+")
        self.entry.bind("<Tab>", lambda e=None: self.close(), add="+")
        self.entry.bind("<Return>", self._enter, add="+")
        self._hook_global()

    # one set of app-wide bindings closes the list when you click or scroll somewhere else
    def _hook_global(self):
        if SuggestBox._hooked:
            return
        SuggestBox._hooked = True
        root = self.winfo_toplevel()
        root.bind_all("<Button-1>", SuggestBox._outside, add="+")
        root.bind_all("<MouseWheel>", SuggestBox._outside, add="+")
        root.bind_all("<<NotebookTabChanged>>", lambda e=None: SuggestBox._close_active(), add="+")
        root.bind("<Configure>", lambda e: SuggestBox._close_active() if e.widget is root else None, add="+")

    @staticmethod
    def _close_active():
        box = SuggestBox._active
        if box is not None:
            try:
                box.close()
            except tk.TclError:
                SuggestBox._active = None

    @staticmethod
    def _outside(event):
        box = SuggestBox._active
        if box is None:
            return
        try:
            w = str(event.widget)
            if box._pop is not None and w.startswith(str(box._pop)):
                return
            if w in (str(box.entry), str(box.arrow)):
                return
            box.close()
        except (tk.TclError, AttributeError):
            SuggestBox._active = None

    def _on_key(self, e):
        if len(e.keysym) == 1 or e.keysym in ("BackSpace", "Delete"):
            self.typed = True

    def _enter(self, _e=None):
        value = self.var.get().strip()
        self.close()
        if value and self.on_enter:
            self.on_enter(value)
        return "break"

    def toggle(self):
        self.close() if self._pop is not None else self.open()

    def close(self):
        pop, self._pop = self._pop, None
        if SuggestBox._active is self:
            SuggestBox._active = None
        if pop is not None:
            try:
                pop.destroy()
            except tk.TclError:
                pass

    def open(self):
        SuggestBox._close_active()
        values = list(self.get_values() or [])
        self._pop = pop = tk.Toplevel(self)
        SuggestBox._active = self
        pop.overrideredirect(True)
        pop.configure(bg=theme.BORDER)
        self._values = values
        self._body = tk.Frame(pop, bg=theme.PANEL2)
        self._body.pack(fill="both", expand=True, padx=1, pady=1)
        self._fill()
        self._place()
        self.entry.focus_set()

    def _fill(self):
        """(Re)build the rows. Called on open and after a ✕, so the list shrinks in place."""
        for w in self._body.winfo_children():
            w.destroy()
        ui = theme.F["ui"]
        if not self._values:
            tk.Label(self._body, text="Nothing saved yet: just type.", bg=theme.PANEL2, fg=theme.MUTED,
                     font=(ui, 10), padx=10, pady=6, anchor="w").pack(fill="x")
            return
        n = len(self._values)
        canvas = tk.Canvas(self._body, bg=theme.PANEL2, highlightthickness=0, bd=0,
                           height=min(n, self.MAX_ROWS) * self.ROW_H, width=max(self.winfo_width(), 240))
        canvas.pack(side="left", fill="both", expand=True)
        rows = tk.Frame(canvas, bg=theme.PANEL2)
        win = canvas.create_window((0, 0), window=rows, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        rows.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        if n > self.MAX_ROWS:
            bar = ttk.Scrollbar(self._body, orient="vertical", command=canvas.yview)
            bar.pack(side="right", fill="y")
            canvas.configure(yscrollcommand=bar.set)

        def wheel(e):
            if n > self.MAX_ROWS:
                up = wheel_notches(getattr(e, "num", None), getattr(e, "delta", 0)) > 0
                canvas.yview_scroll(-1 if up else 1, "units")
            return "break"                               # the page behind the list must not scroll
        for value in self._values:
            row = tk.Frame(rows, bg=theme.PANEL2, height=self.ROW_H)
            row.pack(fill="x")
            row.pack_propagate(False)
            x = tk.Label(row, text="✕", bg=theme.PANEL2, fg=theme.MUTED, font=(ui, 10), padx=10, cursor="hand2")
            x.pack(side="right", fill="y")
            lbl = tk.Label(row, text=value, bg=theme.PANEL2, fg=theme.FG, font=(ui, 10), anchor="w", padx=10,
                           cursor="hand2")
            lbl.pack(side="left", fill="both", expand=True)
            for w in (row, lbl):
                w.bind("<Button-1>", lambda e=None, v=value: self._pick(v))
                w.bind("<Enter>", lambda e=None, r=row, l=lbl, c=x: [t.configure(bg=theme.ACCENT_BG) for t in (r, l, c)])
                w.bind("<Leave>", lambda e=None, r=row, l=lbl, c=x: [t.configure(bg=theme.PANEL2) for t in (r, l, c)])
            x.bind("<Button-1>", lambda e=None, v=value: (self._remove(v), "break")[1])
            x.bind("<Enter>", lambda e=None, r=row, l=lbl, c=x: ([t.configure(bg=theme.ACCENT_BG) for t in (r, l)],
                                                                 c.configure(bg=theme.ACCENT_BG, fg=theme.RED)))
            x.bind("<Leave>", lambda e=None, r=row, l=lbl, c=x: [t.configure(bg=theme.PANEL2) for t in (r, l)]
                   + [c.configure(bg=theme.PANEL2, fg=theme.MUTED)])
            for w in (row, lbl, x):
                for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):      # Button-4/5 = wheel on Linux (Tk 8.6)
                    w.bind(seq, wheel)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(seq, wheel)

    def _place(self):
        self.update_idletasks()
        pop = self._pop
        pop.update_idletasks()
        w, h = pop.winfo_reqwidth(), pop.winfo_reqheight()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        if y + h > self.winfo_screenheight() - 40:             # no room below: open upwards
            y = max(0, self.winfo_rooty() - h)
        pop.geometry(f"{w}x{h}+{x}+{y}")
        pop.lift()

    def _pick(self, value):
        self.typed = False
        self.var.set(value)
        self.close()
        self.entry.focus_set()
        self.entry.icursor("end")
        if self.on_pick:
            self.on_pick(value)

    def _remove(self, value):
        if self.on_delete:
            self.on_delete(value)
        self._values = [v for v in self._values if v != value]
        if self._pop is not None:
            self._fill()
            self._place()
