"""Small, ordinary Python widgets. Each widget only draws and handles keys."""

from .drawing import Theme, clean_text


class Widget:
    focusable = False

    def __init__(self, x, y, width, height=1):
        self.x, self.y, self.width, self.height = x, y, width, height
        self.visible, self.enabled = True, True
        self.focused = self.hovered = self.pressed = False
        self._flash_remaining = self._flash_elapsed = 0.0
        self._flash_interval, self._flash_colour = 0.3, None

    def flash(self, duration=1.8, interval=0.3, style=None):
        """Alternate highlight/normal colours; duration=0 cancels the effect."""
        if not 0 <= duration < float("inf") or not 0 < interval < float("inf"):
            raise ValueError("Flash needs finite duration >= 0 and interval > 0")
        self._flash_remaining, self._flash_elapsed = duration, 0.0
        self._flash_interval, self._flash_colour = interval, style

    def update_effects(self, seconds):
        self._flash_elapsed += max(0, seconds)
        self._flash_remaining = max(0, self._flash_remaining - max(0, seconds))

    def flash_style(self):
        if (self.enabled and self._flash_remaining > 0
                and int(self._flash_elapsed / self._flash_interval) % 2 == 0):
            return Theme.pressed if self._flash_colour is None else self._flash_colour
        return None

    def bounds(self, x, y, width, height=None):
        self.x, self.y, self.width = x, y, width
        if height is not None:
            self.height = height

    def contains(self, x, y):
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def style(self):
        if not self.enabled:
            return Theme.disabled
        if self.pressed:
            return Theme.pressed
        if self.focused:
            return Theme.focus
        return Theme.hover if self.hovered else Theme.button

    def draw(self, canvas):
        pass

    def activate(self):
        pass

    def mouse(self, event):
        """Optional pointer hook for custom widgets; coordinates are screen cells."""
        pass

    def key(self, event):
        if event.key in ("enter", "space"):
            self.activate()


class Label(Widget):
    def __init__(self, x, y, text="", width=40, style=None):
        super().__init__(x, y, width)
        self.text, self.colour = text, style

    def draw(self, canvas):
        canvas.text(self.x, self.y, self.text, self.colour, self.width)


class Panel(Widget):
    """Decorative box. Add its contents separately, after adding the panel."""

    def __init__(self, x, y, width, height, title=""):
        super().__init__(x, y, width, height)
        self.title = title

    def draw(self, canvas):
        canvas.box(self.x, self.y, self.width, self.height, self.title)


class Button(Widget):
    focusable = True

    def __init__(self, x, y, text, on_click=None, width=None):
        super().__init__(x, y, width if width is not None else len(text) + 4, 3)
        self.text, self.on_click = text, on_click

    def draw(self, canvas):
        canvas.box(self.x, self.y, self.width, 3, style=self.style())
        text = clean_text(self.text)[:max(0, self.width - 2)]
        canvas.text(self.x + 1, self.y + 1, text.center(max(0, self.width - 2)), self.style())

    def activate(self):
        if self.enabled and self.on_click:
            self.on_click()


class Checkbox(Widget):
    focusable = True

    def __init__(self, x, y, text, checked=False, on_change=None, width=None):
        super().__init__(x, y, len(text) + 4 if width is None else width)
        self.text, self.checked, self.on_change = text, checked, on_change

    def draw(self, canvas):
        canvas.text(self.x, self.y, ("[x] " if self.checked else "[ ] ") + self.text,
                    self.style(), self.width)

    def activate(self):
        if self.enabled:
            self.checked = not self.checked
            if self.on_change:
                self.on_change(self.checked)


class TextInput(Widget):
    """Single-line editor: click to focus; arrows, Home/End, Backspace/Delete."""

    focusable = True

    def __init__(self, x, y, width, value="", placeholder="", max_length=80):
        super().__init__(x, y, max(3, width), 3)
        self.max_length = max(0, max_length)
        self.value = clean_text(value)[:self.max_length]
        self.placeholder, self.cursor = placeholder, len(self.value)

    def draw(self, canvas):
        canvas.box(self.x, self.y, self.width, 3,
                   style=Theme.accent if self.focused else Theme.border)
        inner = max(1, self.width - 2)
        start = max(0, self.cursor - inner + 1)
        text = self.value[start:] if self.value or self.focused else self.placeholder
        canvas.text(self.x + 1, self.y + 1, text, Theme.input, inner)
        if self.focused:
            char = self.value[self.cursor:self.cursor + 1] or " "
            canvas.text(self.x + 1 + self.cursor - start, self.y + 1, char, Theme.focus)

    def key(self, event):
        if event.key == "left":
            self.cursor = max(0, self.cursor - 1)
        elif event.key == "right":
            self.cursor = min(len(self.value), self.cursor + 1)
        elif event.key == "home":
            self.cursor = 0
        elif event.key == "end":
            self.cursor = len(self.value)
        elif event.key == "backspace" and self.cursor:
            self.value = self.value[:self.cursor - 1] + self.value[self.cursor:]
            self.cursor -= 1
        elif event.key == "delete":
            self.value = self.value[:self.cursor] + self.value[self.cursor + 1:]
        elif event.text and event.text.isprintable() and len(self.value) < self.max_length:
            text = clean_text(event.text)[:self.max_length - len(self.value)]
            self.value = self.value[:self.cursor] + text + self.value[self.cursor:]
            self.cursor += len(text)


class ProgressBar(Widget):
    def __init__(self, x, y, width, value=0):
        super().__init__(x, y, width)
        self.value = value

    def draw(self, canvas):
        value = min(1.0, max(0.0, self.value))
        bar_width = max(0, self.width - 5)
        filled = round(bar_width * value)
        canvas.text(self.x, self.y, "━" * filled, Theme.accent)
        canvas.text(self.x + filled, self.y, "─" * (bar_width - filled), Theme.border)
        canvas.text(self.x + bar_width, self.y, f" {value:3.0%}", Theme.accent,
                    min(5, self.width))
