"""The event loop: input -> update widget state -> draw changed rows."""

import time

from .drawing import Canvas, Theme
from .effects import ToastStack
from .dialogs import Dialog
from .terminal import Terminal


class App:
    def __init__(self, min_width=40, min_height=12):
        self.widgets = []
        self.focus = self.capture = None
        self.running = False
        self.min_width, self.min_height = min_width, min_height
        self.width = self.height = 0
        self.too_small = False
        self.mouse_clicks = 0
        self.toasts = ToastStack()
        self._toast_press = None
        self.dialog = None
        self._dialog_focus = self._dialog_result = None
        self.on_tick = lambda seconds: None
        self.on_resize = lambda width, height: None

    def add(self, widget):
        self.widgets.append(widget)
        return widget

    def stop(self):
        self.running = False

    def notify(self, message, kind="info", duration=3.0):
        """Show a temporary toast without taking keyboard focus."""
        return self.toasts.add(message, kind, duration)

    def update(self, seconds):
        self.toasts.update(seconds)
        for widget in self.widgets + (self.dialog.buttons if self.dialog else []):
            widget.update_effects(seconds)
        self.on_tick(seconds)

    def input_widgets(self):
        return self.dialog.buttons if self.dialog else self.widgets

    def show_dialog(self, title, message, buttons=("OK",), on_result=None):
        if self.dialog:
            raise RuntimeError("Close the current dialog before opening another")
        dialog = Dialog(title, message, buttons, self.close_dialog)
        self.cancel_press()
        self._toast_press = None
        self._dialog_focus, self._dialog_result = self.focus, on_result
        self.dialog = dialog
        self.set_focus(dialog.buttons[0])

    def close_dialog(self, result=None):
        if self.dialog is None:
            return
        callback, previous = self._dialog_result, self._dialog_focus
        self.cancel_press()
        self.dialog = self._dialog_focus = self._dialog_result = None
        self.set_focus(previous)
        if callback:
            callback(result)

    def available(self, widget):
        return (widget is not None and widget in self.input_widgets() and widget.visible
                and widget.enabled and widget.focusable)

    def set_focus(self, widget):
        if self.focus:
            self.focus.focused = False
        self.focus = widget if self.available(widget) else None
        if self.focus:
            self.focus.focused = True

    def cancel_press(self):
        if self.capture:
            self.capture.pressed = False
        self.capture = None

    def dispatch(self, event):
        if event.kind == "key" and event.key == "escape" and self.dialog:
            self.close_dialog()
            return
        if event.kind == "key" and event.key in ("escape", "quit"):
            self.stop()
            return
        if event.kind in ("blur", "resize"):
            self.cancel_press()
            self._toast_press = None
            for widget in self.input_widgets():
                widget.hovered = False
            return
        if self.too_small:
            return
        if self.dialog:
            self.dialog.layout(self.width, self.height)
        if not self.available(self.focus):
            self.set_focus(None)
        if event.kind == "key":
            if event.key == "tab":
                choices = [w for w in self.input_widgets() if self.available(w)]
                if choices:
                    step = -1 if event.shift else 1
                    index = choices.index(self.focus) if self.focus in choices else (0 if event.shift else -1)
                    self.set_focus(choices[(index + step) % len(choices)])
            elif self.focus:
                self.focus.key(event)
            return
        if event.kind not in ("move", "down", "up", "scroll"):
            return
        toast = None if self.dialog else self.toasts.hit(event.x, event.y, self.width, self.height)
        if toast is not None or self._toast_press is not None:
            # Consume the whole gesture, even if the toast expires before release.
            self.cancel_press()
            for widget in self.widgets:
                widget.hovered = False
            if event.kind == "down":
                self._toast_press = toast
            elif event.kind == "up":
                if toast is not None and toast is self._toast_press:
                    self.toasts.dismiss(toast)
                self._toast_press = None
            return
        target = next((w for w in reversed(self.input_widgets())
                       if self.available(w) and w.contains(event.x, event.y)), None)
        for widget in self.input_widgets():
            widget.hovered = widget is target
        if event.kind == "scroll":
            if target:
                target.mouse(event)
        elif event.kind == "down":
            self.cancel_press()
            if target is not None or self.dialog is None:
                self.set_focus(target)
            self.capture = target
            if target:
                target.pressed = True
                target.mouse(event)
        elif event.kind == "move" and self.capture:
            self.capture.pressed = self.capture is target
            self.capture.mouse(event)
        elif event.kind == "move" and target:
            target.mouse(event)
        elif event.kind == "up":
            captured = self.capture
            self.cancel_press()
            if self.available(captured):
                captured.mouse(event)
            # Releasing outside the pressed widget cancels the click.
            if captured is not None and captured is target:
                self.mouse_clicks += 1
                captured.activate()

    def render(self):
        canvas = Canvas(self.width, self.height)
        if self.too_small:
            canvas.text(1, 1, "Please enlarge the terminal", Theme.accent)
            canvas.text(1, 3, f"Need {self.min_width + 1} columns x {self.min_height} rows.")
            canvas.text(1, 5, "Esc / Ctrl+C to exit", Theme.muted)
        else:
            for widget in self.widgets:
                if widget.visible:
                    widget.draw(canvas)
                    style = widget.flash_style()
                    if style is not None:
                        canvas.highlight(widget.x, widget.y, widget.width, widget.height, style)
            self.toasts.draw(canvas)
            if self.dialog:
                canvas.highlight(0, 0, self.width, self.height, Theme.muted)
                self.dialog.draw(canvas)
        return canvas

    def run(self):
        previous = None
        self.running = True
        try:
            with Terminal() as terminal:
                last_time = time.monotonic()
                while self.running:
                    width, height = terminal.size()
                    if (width, height) != (self.width, self.height):
                        self.width, self.height = width, height
                        self.cancel_press()
                        self.too_small = width < self.min_width or height < self.min_height
                        if not self.too_small:
                            self.on_resize(width, height)
                    now = time.monotonic()
                    self.update(now - last_time)
                    last_time = now
                    if self.focus and not self.available(self.focus):
                        self.set_focus(None)
                    canvas = self.render()
                    terminal.write(canvas.changes(previous))
                    previous = canvas
                    for event in terminal.read():
                        self.dispatch(event)
                        if not self.running:
                            break
        finally:
            self.running = False
            self.cancel_press()
