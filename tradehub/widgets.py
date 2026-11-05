"""Shared widgets: scrollable page, placeholder entry, 2-step delete button, auto-height text."""
import tkinter as tk
from tkinter import ttk

from . import theme


class ScrollFrame(ttk.Frame):
    """Vertically scrollable area. Put content into `.inner`."""

    def __init__(self, master, bg=None, **kw):
        super().__init__(master, **kw)
        bg = bg or theme.PANEL
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
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
