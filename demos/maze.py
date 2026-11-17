"""PATHFINDER: a maze editor and animated search lab. No external packages.

Run: python -m demos.maze
Read Maze first (plain Python), then MazeBoard (custom widget), then MazeDemo.
"""


# Allow both `python FILE.py` here and `python -m demos.NAME` from the root.
if not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"

import argparse
import heapq
import random

from cellkit import App, Button, Checkbox, Label, Panel, Theme, Widget


class Maze:
    """Grid data and incremental search, entirely independent of terminal/UI code."""

    columns, rows = 21, 17

    def __init__(self):
        self.start, self.finish = (1, 1), (19, 15)
        self.walls = set()
        self.algorithm = "BFS"
        self.reset_search()

    def inside(self, cell):
        return 0 <= cell[0] < self.columns and 0 <= cell[1] < self.rows

    def neighbours(self, cell):
        x, y = cell
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if self.inside(candidate):
                yield candidate

    def reset_search(self):
        self.state = "ready"
        self.frontier = []
        self.parents = {self.start: None}
        self.cost = {self.start: 0}
        self.visited = set()
        self.path = []
        self.order = 0  # Stable tie-breaking: searches follow neighbour order.

    def generate(self, seed=None):
        """Randomized depth-first carving: every open corridor is connected."""
        rng = random.Random(seed)
        self.start, self.finish = (1, 1), (19, 15)
        self.walls = {(x, y) for y in range(self.rows) for x in range(self.columns)}
        self.walls.remove(self.start)
        stack = [self.start]
        while stack:
            x, y = stack[-1]
            choices = [(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
                       if 0 < x + dx < self.columns - 1 and 0 < y + dy < self.rows - 1
                       and (x + dx, y + dy) in self.walls]
            if choices:
                nx, ny = rng.choice(choices)
                self.walls.remove((nx, ny))
                self.walls.remove(((x + nx) // 2, (y + ny) // 2))
                stack.append((nx, ny))
            else:
                stack.pop()
        self.reset_search()

    def edit(self, cell, tool):
        """Return whether this edit changed the board; protect both endpoints."""
        if not self.inside(cell):
            return False
        if tool == "Wall" and cell not in (self.start, self.finish) and cell not in self.walls:
            self.walls.add(cell)
        elif tool == "Erase" and cell in self.walls:
            self.walls.remove(cell)
        elif tool == "Start" and cell not in (self.start, self.finish):
            self.start = cell
            self.walls.discard(cell)
        elif tool == "Finish" and cell not in (self.start, self.finish):
            self.finish = cell
            self.walls.discard(cell)
        else:
            return False
        self.reset_search()
        return True

    def enqueue(self, cell, distance):
        heuristic = 0
        if self.algorithm == "A*":
            heuristic = abs(cell[0] - self.finish[0]) + abs(cell[1] - self.finish[1])
        # Zero heuristic gives breadth-first expansion on this unit-cost grid.
        heapq.heappush(self.frontier, (distance + heuristic, self.order, cell))
        self.order += 1

    def step(self):
        """Expand one cell. Yield control to the UI between calls, without threads."""
        if self.state in ("found", "no route"):
            return
        if self.state == "ready":
            self.state = "searching"
            self.enqueue(self.start, 0)
        while self.frontier:
            _, _, cell = heapq.heappop(self.frontier)
            if cell not in self.visited:
                break
        else:
            self.state = "no route"
            return
        self.visited.add(cell)
        if cell == self.finish:
            while cell is not None:
                self.path.append(cell)
                cell = self.parents[cell]
            self.path.reverse()
            self.state = "found"
            return
        for neighbour in self.neighbours(cell):
            distance = self.cost[cell] + 1
            if neighbour not in self.walls and distance < self.cost.get(neighbour, float("inf")):
                self.cost[neighbour] = distance
                self.parents[neighbour] = cell
                self.enqueue(neighbour, distance)
        if not self.frontier:
            self.state = "no route"


class MazeBoard(Widget):
    """A whole interactive canvas in one widget: drawing, dragging, and arrow keys."""

    focusable = True
    FLOOR = "38;2;45;60;80;48;2;16;22;34"
    WALL = "38;2;102;123;151;48;2;16;22;34"
    SEEN = "38;2;92;160;224;48;2;25;48;73"
    FRONTIER = "38;2;192;151;245;48;2;56;38;80"
    PATH = "1;38;2;255;214;131;48;2;97;67;31"
    START = "1;38;2;16;22;34;48;2;91;224;197"
    FINISH = "1;38;2;16;22;34;48;2;255;145;150"

    def __init__(self, model, on_edit):
        super().__init__(0, 0, model.columns * 2, model.rows)
        self.model, self.on_edit = model, on_edit
        self.cursor = model.start
        self.last_painted = None

    def draw(self, canvas):
        path = set(self.model.path)
        for y in range(self.model.rows):
            for x in range(self.model.columns):
                cell = (x, y)
                text, style = "· ", self.FLOOR
                if cell in self.model.walls:
                    text, style = "██", self.WALL
                elif cell in path:
                    text, style = "◆ ", self.PATH
                elif cell in self.model.visited:
                    text, style = "· ", self.SEEN
                elif cell in self.model.parents:
                    text, style = "· ", self.FRONTIER
                if cell == self.model.start:
                    text, style = "S ", self.START
                elif cell == self.model.finish:
                    text, style = "F ", self.FINISH
                if self.focused and cell == self.cursor:
                    style += ";4;7"  # Underline and reverse video for the keyboard cursor.
                canvas.text(self.x + x * 2, self.y + y, text, style)

    def mouse(self, event):
        cell = ((event.x - self.x) // 2, event.y - self.y)
        if not self.model.inside(cell):
            self.last_painted = None
            return
        if event.kind == "down":
            self.last_painted = None
        if event.kind == "down" or (event.kind == "move" and self.pressed):
            self.cursor = cell
            # Interpolate a staircase between samples so fast drags leave no gaps.
            x, y = self.last_painted if self.last_painted is not None else cell
            while (x, y) != cell:
                self.on_edit((x, y))
                if x != cell[0]:
                    x += 1 if x < cell[0] else -1
                else:
                    y += 1 if y < cell[1] else -1
            self.on_edit(cell)
            self.last_painted = cell

    def key(self, event):
        moves = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}
        if event.key in moves:
            dx, dy = moves[event.key]
            self.cursor = (max(0, min(self.model.columns - 1, self.cursor[0] + dx)),
                           max(0, min(self.model.rows - 1, self.cursor[1] + dy)))
        elif event.key in ("enter", "space"):
            self.on_edit(self.cursor)


class Legend(Widget):
    def __init__(self):
        super().__init__(0, 0, 42)

    def draw(self, canvas):
        for offset, text, style in ((0, " S ", MazeBoard.START), (4, "start", Theme.muted),
                                    (10, " F ", MazeBoard.FINISH), (14, "finish", Theme.muted),
                                    (22, " seen ", MazeBoard.SEEN), (30, " path ", MazeBoard.PATH)):
            canvas.text(self.x + offset, self.y, text, style)


class MazeDemo:
    def __init__(self):
        self.app = App(min_width=79, min_height=31)
        self.model = Maze()
        self.model.generate(seed=7)
        self.tool = "Wall"
        self.running = False
        self.elapsed = 0.0
        add = self.app.add
        add(Label(2, 1, "P A T H F I N D E R   /   THE MAZE LAB", 60, Theme.warning))
        add(Label(2, 2, "Paint a world. Find a way through it.", 60, Theme.muted))
        self.stats = add(Label(2, 3, "", 70, Theme.accent))
        self.map_panel = add(Panel(2, 5, 47, 23, "INTERACTIVE CANVAS"))
        self.controls = add(Panel(51, 5, 26, 23, "CONTROLS"))
        self.board = add(MazeBoard(self.model, self.edit))
        self.legend = add(Legend())
        self.run_button = add(Button(0, 7, "Run search", self.toggle_run, width=22))
        self.step_button = add(Button(0, 10, "Step", self.single_step, width=10))
        self.clear_button = add(Button(0, 10, "Clear", self.clear_search, width=10))
        self.algorithm_button = add(Button(0, 13, "Search: BFS", self.switch_algorithm, width=22))
        self.tools = {}
        for name in ("Wall", "Erase", "Start", "Finish"):
            self.tools[name] = add(Button(0, 0, name, lambda name=name: self.set_tool(name), width=10))
        self.new_button = add(Button(0, 22, "New maze", self.new_maze, width=10))
        self.blank_button = add(Button(0, 22, "Blank", self.blank, width=10))
        self.fast = add(Checkbox(0, 26, "Fast animation", width=22))
        self.hint = add(Label(2, 29, "", 75, Theme.warning))
        self.footer = add(Label(2, 30, "Drag: paint | Tab: focus | Arrows: move | Space: edit | Esc: exit", 75, Theme.muted))
        self.app.on_resize = self.layout
        self.app.on_tick = self.tick
        self.app.set_focus(self.board)
        self.tick(0)

    def set_tool(self, name):
        self.tool = name

    def edit(self, cell):
        if self.model.edit(cell, self.tool):
            self.running = False
            self.elapsed = 0.0

    def clear_search(self):
        self.running = False
        self.elapsed = 0.0
        self.model.reset_search()

    def new_maze(self):
        self.clear_search()
        self.model.generate()

    def blank(self):
        self.model.walls.clear()
        self.clear_search()

    def switch_algorithm(self):
        self.model.algorithm = "A*" if self.model.algorithm == "BFS" else "BFS"
        self.clear_search()

    def toggle_run(self):
        if self.model.state in ("found", "no route"):
            self.clear_search()
        self.running = not self.running
        self.elapsed = 0.0

    def single_step(self):
        self.running = False
        self.elapsed = 0.0
        self.model.step()

    def layout(self, width, height):
        left_width = width - 32
        side_x = width - 28
        self.map_panel.bounds(2, 5, left_width, height - 8)
        self.controls.bounds(side_x, 5, 26, height - 8)
        self.board.bounds(2 + (left_width - self.board.width) // 2,
                          7 + (height - 31) // 2, self.board.width)
        self.legend.bounds(self.board.x, height - 5, 42)
        x = side_x + 2
        self.run_button.bounds(x, 7, 22)
        self.step_button.bounds(x, 10, 10)
        self.clear_button.bounds(x + 12, 10, 10)
        self.algorithm_button.bounds(x, 13, 22)
        for i, button in enumerate(self.tools.values()):
            button.bounds(x + (i % 2) * 12, 16 + (i // 2) * 3, 10)
        self.new_button.bounds(x, 22, 10)
        self.blank_button.bounds(x + 12, 22, 10)
        self.fast.bounds(x, 26, 22)
        self.hint.bounds(2, height - 2, width - 4)
        self.footer.bounds(2, height - 1, width - 4)

    def tick(self, seconds):
        if self.running:
            self.elapsed += min(seconds, 0.25)
            interval = 0.005 if self.fast.checked else 0.045
            while self.elapsed >= interval and self.model.state not in ("found", "no route"):
                self.model.step()
                self.elapsed -= interval
            if self.model.state in ("found", "no route"):
                self.running = False
                found = self.model.state == "found"
                self.app.notify("Route found!" if found else "No route. Try erasing a wall.",
                                kind="success" if found else "warning")
                self.run_button.flash()
        state = self.model.state.upper()
        if state == "SEARCHING" and not self.running:
            state = "PAUSED"
        distance = str(len(self.model.path) - 1) if self.model.path else "--"
        self.stats.text = f"{state}  /  {self.model.algorithm}  /  Explored {len(self.model.visited):03d}  /  Route {distance} steps"
        self.run_button.text = "Pause" if self.running else "Run search"
        self.step_button.enabled = self.model.state not in ("found", "no route")
        self.algorithm_button.text = "Search: " + self.model.algorithm
        for name, button in self.tools.items():
            button.text = f"[{name}]" if name == self.tool else name
        if self.model.state == "found":
            self.hint.text = "Route found! Switch BFS / A* to compare, or edit the maze."
        elif self.model.state == "no route":
            self.hint.text = "No route exists. Erase a wall to open a passage, then run again."
        else:
            self.hint.text = f"Tool: {self.tool.upper()}  /  Click or drag on the map. Clear resets search only."

    def run(self):
        self.app.run()


PALETTES = {
    "violet": {
        "background": "1C132B", "text": "F1E8FF", "muted": "B7A0CF",
        "accent": "F19FD9", "wall": "9878BC", "border": "654C80",
        "surface": "39264F", "hover": "54366F",
    },
    "amber": {
        "background": "241B13", "text": "FFF0D5", "muted": "C5AB85",
        "accent": "FFBC69", "wall": "BA9564", "border": "796044",
        "surface": "483323", "hover": "684A2D",
    },
    "ocean": {
        "background": "101622", "text": "CDD7E6", "muted": "8194AE",
        "accent": "5BE0C5", "wall": "667B97", "border": "394C65",
        "surface": "26364C", "hover": "375573",
    },
}


def apply_palette(name):
    """Set the process-wide colours before creating widgets. Values are RGB hex."""
    palette = PALETTES[name]
    background = palette["background"]

    def colour(foreground, back=background, bold=False):
        def rgb(value):
            return ";".join(str(int(value[i:i + 2], 16)) for i in (0, 2, 4))
        return ("1;" if bold else "") + f"38;2;{rgb(foreground)};48;2;{rgb(back)}"

    Theme.normal = colour(palette["text"])
    Theme.muted = colour(palette["muted"])
    Theme.accent = colour(palette["accent"], bold=True)
    Theme.border = colour(palette["border"])
    Theme.button = colour(palette["text"], palette["surface"], bold=True)
    Theme.focus = colour(background, palette["accent"], bold=True)
    Theme.hover = colour(palette["text"], palette["hover"], bold=True)
    Theme.pressed = colour(background, "FFD683", bold=True)
    Theme.disabled = colour(palette["muted"], palette["surface"])
    Theme.warning = colour("FFD683")
    Theme.error = colour("FF9196", bold=True)
    Theme.input = colour(palette["text"], palette["surface"])
    MazeBoard.FLOOR = colour(palette["border"])
    MazeBoard.WALL = colour(palette["wall"])
    MazeBoard.SEEN = colour("78B9EF", "253D5A")
    MazeBoard.FRONTIER = colour("D3B0FF", "563875")
    MazeBoard.PATH = colour("FFD683", "61431F", bold=True)
    MazeBoard.START = colour(background, "5BE0C5", bold=True)
    MazeBoard.FINISH = colour(background, "FF9196", bold=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive terminal maze lab")
    parser.add_argument("--theme", choices=PALETTES, default="violet",
                        help="colour scheme (default: violet)")
    options = parser.parse_args()
    apply_palette(options.theme)
    try:
        MazeDemo().run()
    except (RuntimeError, OSError) as error:
        raise SystemExit(f"CellKit: {error}") from None
