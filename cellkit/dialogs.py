"""A centred message dialog. App owns its focus and blocks background input."""

import textwrap

from .drawing import Theme, clean_text
from .widgets import Button


class Dialog:
    def __init__(self, title, message, choices, on_close):
        if not 1 <= len(choices) <= 3 or any(not isinstance(choice, str) or not choice for choice in choices):
            raise ValueError("Dialogs need one to three non-empty button labels")
        self.title, self.message = title, str(message)
        self.buttons = [Button(0, 0, choice, lambda choice=choice: on_close(choice)) for choice in choices]

    def layout(self, width, height):
        self.width = max(12, min(70, width - 4))
        lines = []
        for paragraph in self.message.splitlines():
            lines.extend(textwrap.wrap(clean_text(paragraph), self.width - 4) or [""])
        maximum = max(1, height - 11)
        self.lines = lines[:maximum] or [""]
        if len(lines) > maximum:
            self.lines[-1] = self.lines[-1][:self.width - 7] + "..."
        self.height = len(self.lines) + 7
        self.x, self.y = (width - self.width) // 2, (height - self.height) // 2
        size = (self.width - 4 - 2 * (len(self.buttons) - 1)) // len(self.buttons)
        for index, button in enumerate(self.buttons):
            button.bounds(self.x + 2 + index * (size + 2), self.y + self.height - 4, size)

    def draw(self, canvas):
        self.layout(canvas.width, canvas.height)
        canvas.box(self.x, self.y, self.width, self.height, self.title, Theme.accent)
        for index, line in enumerate(self.lines):
            canvas.text(self.x + 2, self.y + 2 + index, line, Theme.normal, self.width - 4)
        for button in self.buttons:
            button.draw(canvas)
