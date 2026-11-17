"""Search correctness and pointer routing for the second demo."""

from collections import deque
import unittest

from demos.maze import Maze, MazeDemo
from cellkit.terminal import Event


def solve(model):
    for _ in range(model.columns * model.rows + 1):
        model.step()
        if model.state in ("found", "no route"):
            return
    raise AssertionError("Search did not terminate")


def shortest_distance(model):
    """Independent queue-based reference, not the demo's priority queue."""
    queue = deque([(model.start, 0)])
    seen = {model.start}
    while queue:
        cell, distance = queue.popleft()
        if cell == model.finish:
            return distance
        for neighbour in model.neighbours(cell):
            if neighbour not in model.walls and neighbour not in seen:
                seen.add(neighbour)
                queue.append((neighbour, distance + 1))
    return None


class MazeSearchTests(unittest.TestCase):
    def test_generated_mazes_and_both_searches_have_valid_shortest_routes(self):
        for seed in range(8):
            model = Maze()
            model.generate(seed)
            # Add loops to some mazes, testing alternate paths as well as trees.
            if seed % 2:
                model.walls.difference_update((x, 8) for x in range(1, 20))
            expected = shortest_distance(model)
            self.assertIsNotNone(expected)
            for algorithm in ("BFS", "A*"):
                model.algorithm = algorithm
                model.reset_search()
                solve(model)
                self.assertEqual(model.state, "found")
                self.assertEqual(len(model.path) - 1, expected)
                self.assertEqual(model.path[0], model.start)
                self.assertEqual(model.path[-1], model.finish)
                self.assertFalse(set(model.path) & model.walls)
                for first, second in zip(model.path, model.path[1:]):
                    self.assertEqual(abs(first[0] - second[0]) + abs(first[1] - second[1]), 1)

    def test_no_route_and_editing_resets_search(self):
        model = Maze()
        model.walls = set(model.neighbours(model.start))
        solve(model)
        self.assertEqual(model.state, "no route")
        self.assertTrue(model.edit((2, 1), "Erase"))
        self.assertEqual(model.state, "ready")
        solve(model)
        self.assertEqual(model.state, "found")

    def test_endpoints_are_distinct_and_cannot_be_walled(self):
        model = Maze()
        self.assertFalse(model.edit(model.start, "Wall"))
        self.assertFalse(model.edit(model.finish, "Start"))
        self.assertFalse(model.edit((-1, 0), "Finish"))
        model.walls.add((3, 3))
        self.assertTrue(model.edit((3, 3), "Finish"))
        self.assertEqual(model.finish, (3, 3))
        self.assertNotIn(model.finish, model.walls)


class MazeInteractionTests(unittest.TestCase):
    def setUp(self):
        self.demo = MazeDemo()
        self.demo.layout(79, 31)
        self.demo.blank()

    def pointer(self, kind, cell):
        board = self.demo.board
        self.demo.app.dispatch(Event(kind, x=board.x + cell[0] * 2 + 1,
                                     y=board.y + cell[1]))

    def test_drag_fills_gaps_and_hover_does_not_paint(self):
        self.pointer("down", (2, 2))
        self.pointer("move", (7, 2))
        self.pointer("up", (7, 2))
        self.pointer("move", (8, 2))
        self.assertEqual(self.demo.model.walls, {(x, 2) for x in range(2, 8)})
        self.demo.set_tool("Erase")
        self.pointer("down", (4, 2))
        self.pointer("up", (4, 2))
        self.assertNotIn((4, 2), self.demo.model.walls)

    def test_drag_outside_and_back_does_not_paint_across_board(self):
        self.pointer("down", (2, 2))
        self.pointer("move", (-1, 2))
        self.pointer("move", (8, 2))
        self.pointer("up", (8, 2))
        self.assertEqual(self.demo.model.walls, {(2, 2), (8, 2)})

    def test_blur_cancels_paint_and_keyboard_edits(self):
        self.pointer("down", (2, 2))
        self.demo.app.dispatch(Event("blur"))
        self.pointer("move", (8, 2))
        self.assertEqual(self.demo.model.walls, {(2, 2)})
        self.demo.app.set_focus(self.demo.board)
        self.demo.app.dispatch(Event("key", key="right"))
        self.demo.app.dispatch(Event("key", key="space"))
        self.assertIn((3, 2), self.demo.model.walls)

    def test_edit_stops_animation_and_search_can_restart(self):
        self.demo.toggle_run()
        self.demo.tick(0.1)
        self.assertTrue(self.demo.model.visited)
        self.pointer("down", (3, 3))
        self.pointer("up", (3, 3))
        self.assertFalse(self.demo.running)
        self.assertEqual(self.demo.model.state, "ready")
        self.demo.fast.checked = True
        self.demo.toggle_run()
        for _ in range(30):
            self.demo.tick(0.25)
        self.assertEqual(self.demo.model.state, "found")
        self.assertFalse(self.demo.running)

    def test_layout_stays_inside_panels_and_screen(self):
        for width, height in ((79, 31), (109, 36), (159, 48)):
            self.demo.layout(width, height)
            for widget in self.demo.app.widgets:
                self.assertGreaterEqual(widget.x, 0)
                self.assertGreaterEqual(widget.y, 0)
                self.assertLessEqual(widget.x + widget.width, width)
                self.assertLessEqual(widget.y + widget.height, height)
            board, panel = self.demo.board, self.demo.map_panel
            self.assertGreater(board.x, panel.x)
            self.assertLess(board.x + board.width, panel.x + panel.width)
            self.assertLess(board.y + board.height, self.demo.legend.y)


if __name__ == "__main__":
    unittest.main()
