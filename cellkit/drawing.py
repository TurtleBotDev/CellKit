"""Character-cell drawing. Coordinates start at (0, 0), in the top left."""

import unicodedata


class Theme:
    """ANSI colours kept in one place. Change these to restyle the whole UI."""

    normal = "38;2;205;215;230;48;2;16;22;34"
    muted = "38;2;129;148;174;48;2;16;22;34"
    accent = "1;38;2;91;224;197;48;2;16;22;34"
    border = "38;2;57;76;101;48;2;16;22;34"
    button = "1;38;2;218;230;243;48;2;38;54;76"
    focus = "1;38;2;17;28;41;48;2;91;224;197"
    hover = "1;38;2;235;248;255;48;2;55;85;115"
    pressed = "1;38;2;16;22;34;48;2;244;195;101"
    disabled = "38;2;106;120;139;48;2;28;36;49"
    warning = "38;2;244;195;101;48;2;16;22;34"
    error = "1;38;2;255;145;150;48;2;16;22;34"
    input = "38;2;230;238;249;48;2;28;40;59"


def clean_text(value):
    """Keep one printable character per cell; never execute embedded escapes.

    Full emoji/CJK/grapheme support needs a more sophisticated width engine.
    For this small engine, wide characters and control characters become '?'.
    """
    return "".join(
        char if char.isprintable()
        and not unicodedata.category(char).startswith("M")
        and unicodedata.east_asian_width(char) not in ("W", "F") else "?"
        for char in str(value)
    )


class Canvas:
    """A tiny off-screen grid. Every drawing operation clips to its boundaries."""

    def __init__(self, width, height):
        self.width, self.height = max(0, width), max(0, height)
        self.rows = [[(" ", Theme.normal)] * self.width for _ in range(self.height)]

    def text(self, x, y, value, style=None, width=None):
        style = Theme.normal if style is None else style
        if not 0 <= y < self.height:
            return
        value = clean_text(value)
        if width is not None:
            value = value[:max(0, width)].ljust(max(0, width))
        for offset, char in enumerate(value):
            if 0 <= x + offset < self.width:
                self.rows[y][x + offset] = (char, style)

    def box(self, x, y, width, height, title="", style=None):
        style = Theme.border if style is None else style
        if width < 2 or height < 2:
            return
        self.text(x, y, "╭" + "─" * (width - 2) + "╮", style)
        for row in range(y + 1, y + height - 1):
            self.text(x, row, "│" + " " * (width - 2) + "│", style)
        self.text(x, y + height - 1, "╰" + "─" * (width - 2) + "╯", style)
        if title:
            self.text(x + 2, y, (" " + title + " ")[:max(0, width - 4)], style)

    def highlight(self, x, y, width, height, style):
        """Recolour a rectangle without changing its text (used by flash effects)."""
        for row in range(max(0, y), min(self.height, y + height)):
            for column in range(max(0, x), min(self.width, x + width)):
                char, _ = self.rows[row][column]
                self.rows[row][column] = (char, style)

    def changes(self, previous=None):
        """Encode only changed rows, then send them together to avoid flicker."""
        resized = (previous is None or
                   (self.width, self.height) != (previous.width, previous.height))
        output = ["\x1b[2J"] if resized else []
        for y, row in enumerate(self.rows):
            if not resized and row == previous.rows[y]:
                continue
            output.append(f"\x1b[{y + 1};1H")
            last_style = None
            for char, style in row:
                if style != last_style:
                    output.append(f"\x1b[0;{style}m")
                    last_style = style
                output.append(char)
        if output:
            output.append("\x1b[0m")
        return "".join(output)
