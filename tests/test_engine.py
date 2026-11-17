import ctypes
import os
import unittest

from demos.dashboard import Dashboard
from cellkit import App, Button, Canvas, Checkbox, Label, TextInput, Theme
from cellkit.drawing import clean_text
from cellkit.terminal import Decoder, Event, InputRecord, KeyRecord, MouseRecord


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.calls = []
        self.button = self.app.add(Button(2, 3, "Go", lambda: self.calls.append("go"), width=10))

    def mouse(self, kind, x=4, y=4):
        self.app.dispatch(Event(kind, x=x, y=y))

    def test_button_fires_once_on_release(self):
        self.mouse("down")
        self.assertTrue(self.button.pressed)
        self.assertEqual(self.calls, [])
        self.mouse("up")
        self.mouse("up")
        self.assertEqual(self.calls, ["go"])
        self.assertEqual(self.app.mouse_clicks, 1)
        self.assertFalse(self.button.pressed)

    def test_drag_out_cancels_and_release_inside_without_press_is_ignored(self):
        self.mouse("down")
        self.mouse("move", 20, 20)
        self.assertFalse(self.button.pressed)
        self.mouse("up", 20, 20)
        self.mouse("up")
        self.assertEqual(self.calls, [])

    def test_press_outside_release_inside_is_not_click(self):
        self.mouse("down", 40, 40)
        self.mouse("up")
        self.assertEqual(self.calls, [])

    def test_disabled_hidden_and_mid_press_disabled_widgets_do_not_fire(self):
        self.button.enabled = False
        self.mouse("down")
        self.mouse("up")
        self.button.enabled, self.button.visible = True, False
        self.mouse("down")
        self.mouse("up")
        self.button.visible = True
        self.mouse("down")
        self.button.enabled = False
        self.mouse("up")
        self.assertEqual(self.calls, [])

    def test_blur_and_resize_cancel_press(self):
        for kind in ("blur", "resize"):
            self.mouse("down")
            self.app.dispatch(Event(kind))
            self.mouse("up")
        self.assertEqual(self.calls, [])

    def test_unavailable_widgets_stop_receiving_drag_events(self):
        for change in ("disabled", "hidden", "removed"):
            with self.subTest(change=change):
                self.setUp()
                received = []
                self.button.mouse = lambda event: received.append(event.kind)
                self.mouse("down")
                if change == "disabled":
                    self.button.enabled = False
                elif change == "hidden":
                    self.button.visible = False
                else:
                    self.app.widgets.remove(self.button)
                self.mouse("move")
                self.mouse("up")
                self.assertEqual(received, ["down"])
                self.assertIsNone(self.app.capture)
                self.assertFalse(self.button.pressed)
                self.assertEqual(self.calls, [])

    def test_release_callback_can_cancel_activation(self):
        for change in ("hidden", "dialog"):
            with self.subTest(change=change):
                self.setUp()
                def released(event):
                    if event.kind == "up":
                        if change == "hidden":
                            self.button.visible = False
                        else:
                            self.app.show_dialog("Notice", "Input is now modal")
                self.button.mouse = released
                self.mouse("down")
                self.mouse("up")
                self.assertEqual(self.calls, [])
                self.assertEqual(self.app.mouse_clicks, 0)

    def test_hit_test_edges_are_exclusive(self):
        self.assertTrue(self.button.contains(2, 3))
        self.assertTrue(self.button.contains(11, 5))
        self.assertFalse(self.button.contains(12, 5))
        self.assertFalse(self.button.contains(11, 6))

    def test_tab_skips_disabled_controls_and_wraps_both_directions(self):
        disabled = self.app.add(Button(20, 3, "No"))
        disabled.enabled = False
        checkbox = self.app.add(Checkbox(2, 8, "Option"))
        self.app.dispatch(Event("key", key="tab", shift=True))
        self.assertIs(self.app.focus, checkbox)
        self.app.dispatch(Event("key", key="tab"))
        self.assertIs(self.app.focus, self.button)
        self.app.dispatch(Event("key", key="enter"))
        self.assertEqual(self.calls, ["go"])
        self.assertEqual(self.app.mouse_clicks, 0)
        self.app.dispatch(Event("key", key="tab"))
        self.app.dispatch(Event("key", key="space"))
        self.assertTrue(checkbox.checked)

    def test_resize_warning_blocks_clicks_but_allows_exit(self):
        self.app.too_small = True
        self.app.running = True
        self.mouse("down")
        self.mouse("up")
        self.assertEqual(self.calls, [])
        self.app.dispatch(Event("key", key="escape"))
        self.assertFalse(self.app.running)

    def test_text_editing_and_length_limit(self):
        field = TextInput(1, 1, 8, "abc", max_length=5)
        field.key(Event("key", key="left"))
        field.key(Event("key", text="X"))
        self.assertEqual(field.value, "abXc")
        field.key(Event("key", key="backspace"))
        field.key(Event("key", key="delete"))
        self.assertEqual(field.value, "ab")
        field.key(Event("key", key="home"))
        field.key(Event("key", text="123456"))
        self.assertEqual(field.value, "123ab")
        field.key(Event("key", key="end"))
        self.assertEqual(field.cursor, 5)


class RenderingTests(unittest.TestCase):
    def test_negative_coordinates_clip_without_wrapping(self):
        canvas = Canvas(4, 2)
        canvas.text(-2, 0, "abcdef")
        canvas.text(0, -1, "wrong")
        canvas.text(0, 2, "wrong")
        self.assertEqual("".join(char for char, _ in canvas.rows[0]), "cdef")
        self.assertEqual("".join(char for char, _ in canvas.rows[1]), "    ")

    def test_no_unchanged_redraw_and_shortened_label_erases_old_text(self):
        old = Canvas(10, 2)
        old.text(0, 0, "long text")
        self.assertEqual(old.changes(old), "")
        new = Canvas(10, 2)
        new.text(0, 0, "hi")
        changes = new.changes(old)
        self.assertIn("hi        ", changes)
        self.assertNotIn("\x1b[2;1H", changes)
        self.assertIn("\x1b[2J", Canvas(8, 2).changes(old))

    def test_untrusted_control_and_wide_text_do_not_break_grid(self):
        self.assertEqual(clean_text("a\x1bb\n中🙂e\u0301"), "a?b???e?")
        canvas = Canvas(15, 1)
        canvas.text(0, 0, "\x1b[31m")
        self.assertNotIn("\x1b[31m", canvas.changes())

    def test_styles_cannot_inject_terminal_commands(self):
        for style in ("31m\x1b[2J", "31mhidden", "\x1b]0;title\x07", "\u0661", 31):
            for method in ("text", "highlight"):
                with self.subTest(style=style, method=method):
                    canvas = Canvas(3, 1)
                    if method == "text":
                        canvas.text(0, 0, "abc", style)
                    else:
                        canvas.highlight(0, 0, 3, 1, style)
                    with self.assertRaises(ValueError):
                        canvas.changes()
        canvas = Canvas(1, 1)
        canvas.text(0, 0, "x", "1;38;2;255;0;0")
        self.assertIn("\x1b[0;1;38;2;255;0;0mx", canvas.changes())

    def test_dashboard_layout_fits_at_supported_sizes(self):
        dashboard = Dashboard()
        for width, height in ((79, 31), (109, 36), (159, 48)):
            dashboard.layout(width, height)
            dashboard.tick(0)
            for widget in dashboard.app.widgets:
                if widget.visible:
                    self.assertGreaterEqual(widget.x, 0)
                    self.assertGreaterEqual(widget.y, 0)
                    self.assertLessEqual(widget.x + widget.width, width, type(widget).__name__)
                    self.assertLessEqual(widget.y + widget.height, height, type(widget).__name__)

    def test_dashboard_job_lifecycle_and_custom_job(self):
        dashboard = Dashboard()
        dashboard.toggle()
        for _ in range(3):
            dashboard.tick(9)
        self.assertFalse(dashboard.running)
        self.assertEqual(dashboard.finished, 3)
        self.assertFalse(dashboard.start_button.enabled)
        dashboard.name.value = "My report"
        dashboard.add_job()
        dashboard.tick(0)
        self.assertTrue(dashboard.start_button.enabled)
        self.assertEqual(list(dashboard.jobs), ["My report"])
        dashboard.reset()
        self.assertEqual(len(dashboard.jobs), 3)
        self.assertEqual(dashboard.finished, 0)


@unittest.skipUnless(os.name == "nt", "Windows record layouts")
class DecoderTests(unittest.TestCase):
    def test_native_structure_sizes(self):
        self.assertEqual(ctypes.sizeof(KeyRecord), 16)
        self.assertEqual(ctypes.sizeof(MouseRecord), 16)
        self.assertEqual(ctypes.sizeof(InputRecord), 20)

    def test_mouse_origin_drag_doubleclick_and_right_button(self):
        decoder = Decoder()
        record = InputRecord()
        record.kind = 2
        record.data.mouse.position.x, record.data.mouse.position.y = 12, 23
        record.data.mouse.buttons = 1
        down = decoder.decode(record, (10, 20))[0]
        self.assertEqual((down.kind, down.x, down.y), ("down", 2, 3))
        record.data.mouse.flags = 1  # movement while held
        self.assertEqual(decoder.decode(record)[0].kind, "move")
        record.data.mouse.buttons = 0
        self.assertEqual(decoder.decode(record)[0].kind, "up")
        record.data.mouse.buttons, record.data.mouse.flags = 1, 2  # double click down
        self.assertEqual(decoder.decode(record)[0].kind, "down")
        record.data.mouse.buttons = 0
        decoder.decode(record)
        record.data.mouse.buttons = 2  # right button is not a left press
        self.assertEqual(decoder.decode(record)[0].kind, "move")

    def test_key_repeat_shift_tab_and_ctrl_c(self):
        record = InputRecord()
        record.kind = 1
        record.data.key.down = True
        record.data.key.repeat = 3
        record.data.key.code, record.data.key.char = 9, "\t"
        record.data.key.modifiers = 0x10
        events = Decoder().decode(record)
        self.assertEqual(len(events), 3)
        self.assertTrue(events[0].shift)
        self.assertEqual(events[0].key, "tab")
        record.data.key.code, record.data.key.modifiers = 67, 8
        self.assertEqual(Decoder().decode(record)[0].key, "quit")


if __name__ == "__main__":
    unittest.main()
