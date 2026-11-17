"""Scrollable tables and lists, sharing selection and keyboard behaviour."""

from .drawing import Theme, clean_text
from .widgets import Widget


class Table(Widget):
    focusable = True

    def __init__(self, x, y, width, height, columns, rows=(), title="",
                 on_select=None, on_activate=None):
        super().__init__(x, y, width, height)
        self.columns, self.title = list(columns), title
        self.rows = [tuple(row) for row in rows]
        self.selected = 0 if self.rows else None
        self.offset = 0
        self.on_select, self.on_activate = on_select, on_activate
        self._pressed_row = None
        self._double_click = self._drag_scroll = False

    @property
    def page_size(self):
        return max(1, self.height - 2 - bool(self.columns))

    @property
    def selected_row(self):
        return self.rows[self.selected] if self.selected is not None else None

    def set_rows(self, rows, selected=0):
        self.rows = [tuple(row) for row in rows]
        self.offset, self.selected = 0, None
        self._pressed_row = None
        self.select(selected)

    def select(self, index):
        self.selected = max(0, min(index, len(self.rows) - 1)) if self.rows else None
        if self.selected is not None:
            self.offset = min(self.offset, self.selected)
            self.offset = max(self.offset, self.selected - self.page_size + 1)
        if self.on_select:
            self.on_select(self.selected)

    def bounds(self, x, y, width, height=None):
        super().bounds(x, y, width, height)
        self.offset = min(self.offset, max(0, len(self.rows) - self.page_size))

    def scroll(self, amount):
        self.offset = max(0, min(self.offset + amount, len(self.rows) - self.page_size))

    def row_at(self, x, y):
        top = self.y + 1 + bool(self.columns)
        index = self.offset + y - top
        if (self.x < x < self.x + self.width - 2 and top <= y < top + self.page_size
                and 0 <= index < len(self.rows)):
            return index
        return None

    def open_selection(self):
        if self.selected is not None and self.on_activate:
            self.on_activate(self.selected)

    def key(self, event):
        moves = {"up": -1, "down": 1, "pageup": -self.page_size, "pagedown": self.page_size}
        index = self.selected if self.selected is not None else 0
        if event.key in moves:
            self.select(index + moves[event.key])
        elif event.key in ("home", "end"):
            self.select(0 if event.key == "home" else len(self.rows) - 1)
        elif event.key in ("enter", "space"):
            self.open_selection()

    def mouse(self, event):
        if event.kind == "scroll":
            self.scroll(event.delta * 3)
        elif event.kind == "down":
            self._pressed_row = self.row_at(event.x, event.y)
            self._double_click = event.clicks == 2
            self._drag_scroll = event.x == self.x + self.width - 2
        elif event.kind == "up":
            index = self.row_at(event.x, event.y)
            if index is not None and index == self._pressed_row:
                self.select(index)
                if self._double_click:
                    self.open_selection()
            self._pressed_row, self._drag_scroll = None, False
        if self._drag_scroll and (event.kind == "down" or (event.kind == "move" and self.pressed)):
            top = self.y + 1 + bool(self.columns)
            fraction = (event.y - top) / max(1, self.page_size - 1)
            maximum = max(0, len(self.rows) - self.page_size)
            self.offset = max(0, min(maximum, round(fraction * maximum)))

    def row_text(self, row):
        if not self.columns:
            return clean_text(row[0]) if row else ""
        return " │ ".join(clean_text(row[i] if i < len(row) else "")[:size].ljust(size)
                          for i, (_, size) in enumerate(self.columns))

    def draw(self, canvas):
        self.offset = min(self.offset, max(0, len(self.rows) - self.page_size))
        canvas.box(self.x, self.y, self.width, self.height, self.title,
                   Theme.accent if self.focused else Theme.border)
        if self.width < 4 or self.height < 3 + bool(self.columns):
            return
        if self.columns:
            canvas.text(self.x + 1, self.y + 1, self.row_text([name for name, _ in self.columns]),
                        Theme.accent, self.width - 3)
        top = self.y + 1 + bool(self.columns)
        for position in range(self.page_size):
            index = self.offset + position
            if index < len(self.rows):
                selected = index == self.selected
                style = Theme.focus if selected and self.focused else Theme.button if selected else Theme.normal
                canvas.text(self.x + 1, top + position, self.row_text(self.rows[index]), style, self.width - 3)
        if not self.rows:
            canvas.text(self.x + 1, top, "(empty)", Theme.muted, self.width - 3)
        if len(self.rows) > self.page_size:
            thumb = round(self.offset * (self.page_size - 1) / (len(self.rows) - self.page_size))
            for position in range(self.page_size):
                canvas.text(self.x + self.width - 2, top + position,
                            "█" if position == thumb else "│", Theme.accent)


class ListBox(Table):
    """A single-column Table without a header. Callbacks receive a row index."""

    def __init__(self, x, y, width, height, items=(), **kwargs):
        super().__init__(x, y, width, height, [], ((item,) for item in items), **kwargs)

    def set_items(self, items, selected=0):
        self.set_rows(((item,) for item in items), selected)
