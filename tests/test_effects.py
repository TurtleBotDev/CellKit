import unittest

from cellkit import App, Button, Label, Theme
from cellkit.terminal import Event


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.width, self.app.height = 79, 31
        self.calls = []
        self.button = self.app.add(Button(4, 4, "Press", lambda: self.calls.append(1), width=12))
        self.app.set_focus(self.button)

    def colour(self, widget):
        return self.app.render().rows[widget.y][widget.x][1]

    def toast_point(self):
        toast, x, y, width, lines = next(self.app.toasts.layout(79, 31))
        return x + 2, y + 1

    def pointer(self, kind, point):
        self.app.dispatch(Event(kind, x=point[0], y=point[1]))

    def test_flash_alternates_then_restores_focus_style_and_stays_interactive(self):
        self.button.flash(duration=1, interval=0.25)
        self.assertEqual(self.colour(self.button), Theme.pressed)
        self.app.dispatch(Event("key", key="enter"))
        self.assertEqual(self.calls, [1])
        self.app.update(0.25)
        self.assertEqual(self.colour(self.button), Theme.focus)
        self.app.update(0.25)
        self.assertEqual(self.colour(self.button), Theme.pressed)
        self.app.update(0.5)
        self.assertEqual(self.colour(self.button), Theme.focus)

    def test_flash_custom_widget_colour_cancel_and_disable(self):
        label = self.app.add(Label(2, 10, "Hello", width=10))
        label.flash(style=Theme.error)
        self.assertEqual(self.colour(label), Theme.error)
        self.assertEqual(self.app.render().rows[10][2][0], "H")
        label.flash(duration=0)
        self.assertEqual(self.colour(label), Theme.normal)
        self.button.flash()
        self.button.enabled = False
        self.assertEqual(self.colour(self.button), Theme.disabled)

    def test_toast_expires_preserves_focus_and_redraws_underlying_content(self):
        original = self.app.render()
        self.app.notify("Saved!", kind="success", duration=1)
        overlay = self.app.render()
        self.assertNotEqual(overlay.rows, original.rows)
        self.assertIs(self.app.focus, self.button)
        self.app.update(1)
        self.assertEqual(self.app.render().rows, original.rows)
        self.assertTrue(self.app.render().changes(overlay))

    def test_toast_click_dismisses_without_activating_widget_underneath(self):
        self.app.notify("Click me")
        point = self.toast_point()
        self.button.bounds(point[0], point[1], 12)
        self.pointer("down", point)
        self.pointer("up", point)
        self.assertEqual(self.app.toasts.items, [])
        self.assertEqual(self.calls, [])
        self.assertIs(self.app.focus, self.button)

    def test_toast_expiring_during_press_does_not_click_through(self):
        self.app.notify("Short-lived", duration=0.1)
        point = self.toast_point()
        self.button.bounds(point[0], point[1], 12)
        self.pointer("down", point)
        self.app.update(0.2)
        self.pointer("up", point)
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.app._toast_press)

    def test_drag_outside_toast_cancels_dismissal_and_underlying_click(self):
        self.app.notify("Keep me")
        self.pointer("down", self.toast_point())
        self.pointer("up", (5, 5))
        self.assertEqual(len(self.app.toasts.items), 1)
        self.assertEqual(self.calls, [])

    def test_toasts_wrap_cap_stack_and_fit_resized_screen(self):
        for kind in ("info", "success", "warning", "error"):
            self.app.notify("A long message " * 30, kind=kind)
        self.assertEqual(len(self.app.toasts.items), 3)
        for width, height in ((79, 31), (30, 12), (10, 5)):
            bottom = height
            for toast, x, y, size, lines in self.app.toasts.layout(width, height):
                self.assertGreaterEqual(x, 0)
                self.assertLessEqual(x + size, width)
                self.assertGreaterEqual(y, 0)
                self.assertLess(y + len(lines) + 2, bottom)
                self.assertLessEqual(len(lines), 3)
                self.assertTrue(all(len(line) <= size - 4 for line in lines))
                bottom = y

    def test_invalid_timings_and_kind_fail_clearly(self):
        for duration in (-1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                self.button.flash(duration=duration)
            with self.assertRaises(ValueError):
                self.app.notify("Invalid", duration=duration)
        with self.assertRaises(ValueError):
            self.button.flash(interval=0)
        with self.assertRaises(ValueError):
            self.app.notify("Invalid", kind="unknown")


if __name__ == "__main__":
    unittest.main()
