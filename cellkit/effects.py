"""Short-lived toast overlays. No threads or sleeps: the app advances the timers."""

from dataclasses import dataclass
import textwrap

from .drawing import Theme, clean_text


@dataclass(eq=False)
class Toast:
    message: str
    kind: str
    remaining: float


class ToastStack:
    def __init__(self):
        self.items = []

    def add(self, message, kind="info", duration=3.0):
        if kind not in ("info", "success", "warning", "error"):
            raise ValueError("Toast kind must be info, success, warning or error")
        if not 0 < duration < float("inf"):
            raise ValueError("Toast duration must be finite and positive")
        toast = Toast(clean_text(message), kind, duration)
        self.items.append(toast)
        self.items = self.items[-3:]  # Keep the screen readable during bursts.
        return toast

    def update(self, seconds):
        for toast in self.items:
            toast.remaining -= max(0, seconds)
        self.items = [toast for toast in self.items if toast.remaining > 0]

    def dismiss(self, toast):
        if toast in self.items:
            self.items.remove(toast)

    def layout(self, width, height):
        """Newest at bottom right; wrap up to three lines and fit within the screen."""
        box_width = min(44, width - 4)
        bottom = height - 2
        if box_width < 16:
            return
        for toast in reversed(self.items):
            lines = textwrap.wrap(toast.message, width=box_width - 4,
                                  max_lines=3, placeholder="...") or [""]
            y = bottom - len(lines) - 2
            if y < 1:
                break
            yield toast, width - box_width - 2, y, box_width, lines
            bottom = y - 1

    def hit(self, x, y, width, height):
        for toast, left, top, size, lines in self.layout(width, height):
            if left <= x < left + size and top <= y < top + len(lines) + 2:
                return toast
        return None

    def draw(self, canvas):
        styles = {"info": Theme.button, "success": Theme.accent,
                  "warning": Theme.warning, "error": Theme.error}
        for toast, x, y, width, lines in self.layout(canvas.width, canvas.height):
            style = styles[toast.kind]
            canvas.box(x, y, width, len(lines) + 2, toast.kind.upper(), style)
            canvas.text(x + width - 5, y, "[x]", style)
            for offset, line in enumerate(lines):
                canvas.text(x + 2, y + 1 + offset, line, style, width - 4)
