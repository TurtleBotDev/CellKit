import os
import unittest

from cellkit import App, Button, ListBox, Table
from cellkit.terminal import Decoder, Event, InputRecord


class TableTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.width, self.app.height = 79, 31
        self.opened = []
        self.table = self.app.add(Table(2, 2, 45, 8, [("Name", 25), ("Value", 10)],
                                       [(f"Row {i}", i) for i in range(50)],
                                       on_activate=self.opened.append))
        self.app.set_focus(self.table)

    def pointer(self, kind, x=5, y=4, clicks=1):
        self.app.dispatch(Event(kind, x=x, y=y, clicks=clicks))

    def test_wheel_scrolls_without_changing_selection_and_keyboard_reveals_it(self):
        self.app.dispatch(Event("scroll", x=5, y=5, delta=2))
        self.assertEqual(self.table.offset, 6)
        self.assertEqual(self.table.selected, 0)
        self.app.dispatch(Event("key", key="down"))
        self.assertEqual(self.table.selected, 1)
        self.assertEqual(self.table.offset, 1)
        self.app.dispatch(Event("key", key="end"))
        self.assertEqual((self.table.selected, self.table.offset), (49, 45))
        self.app.dispatch(Event("key", key="home"))
        self.app.dispatch(Event("key", key="pagedown"))
        self.assertEqual(self.table.selected, 5)
        self.app.dispatch(Event("key", key="pageup"))
        self.assertEqual((self.table.selected, self.table.offset), (0, 0))

    def test_single_click_selects_and_double_click_opens_once_on_release(self):
        self.pointer("down", y=6)
        self.pointer("up", y=6)
        self.assertEqual(self.table.selected, 2)
        self.assertEqual(self.opened, [])
        self.pointer("down", y=6, clicks=2)
        self.assertEqual(self.opened, [])
        self.pointer("up", y=6)
        self.assertEqual(self.opened, [2])

    def test_clicking_header_or_dragging_to_another_row_does_not_select(self):
        self.pointer("down", y=3)
        self.pointer("up", y=3)
        self.pointer("down", y=5)
        self.pointer("up", y=6)
        self.assertEqual(self.table.selected, 0)
        self.assertEqual(self.opened, [])

    def test_scrollbar_drag_and_data_replacement_clamp_offset(self):
        self.pointer("down", x=45, y=8)
        self.assertEqual(self.table.offset, 45)
        self.pointer("move", x=45, y=4)
        self.assertEqual(self.table.offset, 0)
        self.pointer("up", x=45, y=4)
        self.table.scroll(1000)
        self.table.bounds(2, 2, 45, 12)
        self.assertEqual(self.table.offset, 41)
        self.table.set_rows([])
        self.assertEqual(self.table.offset, 0)
        self.assertIsNone(self.table.selected_row)
        self.app.dispatch(Event("key", key="enter"))
        self.assertEqual(self.opened, [])
        self.app.render()

    def test_lists_share_selection_and_render_without_header(self):
        choices = ListBox(0, 0, 20, 5, ["Alpha", "Beta", "Gamma", "Delta"])
        self.assertEqual(choices.page_size, 3)
        choices.select(3)
        self.assertEqual(choices.offset, 1)
        self.assertEqual(choices.selected_row, ("Delta",))
        choices.set_items(["Only"])
        self.assertEqual((choices.offset, choices.selected), (0, 0))

    def test_focus_loss_cancels_scrollbar_drag(self):
        self.pointer("down", x=45, y=8)
        self.assertEqual(self.table.offset, 45)
        self.app.dispatch(Event("blur"))
        self.pointer("move", x=45, y=4)
        self.assertEqual(self.table.offset, 45)


class DialogTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.width, self.app.height, self.app.running = 79, 31, True
        self.calls = []
        self.background = self.app.add(Button(1, 1, "Background", lambda: self.calls.append("background")))
        self.app.set_focus(self.background)

    def test_dialog_traps_input_and_escape_restores_focus_without_exiting(self):
        self.app.show_dialog("Confirm", "Continue?", ("Cancel", "OK"), self.calls.append)
        first, second = self.app.dialog.buttons
        self.app.dispatch(Event("key", key="tab", shift=True))
        self.assertIs(self.app.focus, second)
        self.app.dispatch(Event("key", key="tab"))
        self.assertIs(self.app.focus, first)
        for kind in ("down", "up"):
            self.app.dispatch(Event(kind, x=2, y=2))
        self.assertEqual(self.calls, [])
        self.assertIs(self.app.focus, first)
        self.app.dispatch(Event("key", key="escape"))
        self.assertTrue(self.app.running)
        self.assertIs(self.app.focus, self.background)
        self.assertEqual(self.calls, [None])

    def test_result_is_delivered_once_and_can_open_followup_dialog(self):
        def answered(result):
            self.calls.append(result)
            self.app.show_dialog("Done", "A follow-up message")
        self.app.show_dialog("Confirm", "Continue?", ("Cancel", "Yes"), answered)
        self.app.render()
        button = self.app.dialog.buttons[1]
        for kind in ("down", "up"):
            self.app.dispatch(Event(kind, x=button.x + 1, y=button.y + 1))
        self.assertEqual(self.calls, ["Yes"])
        self.assertEqual(self.app.dialog.title, "Done")
        self.app.dispatch(Event("key", key="enter"))
        self.assertIsNone(self.app.dialog)
        self.assertIs(self.app.focus, self.background)

    def test_showing_dialog_cancels_background_press(self):
        self.app.dispatch(Event("down", x=2, y=2))
        self.app.show_dialog("Notice", "The background cannot receive this release")
        self.app.dispatch(Event("up", x=2, y=2))
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.app.capture)

    def test_wrapping_and_resize_keep_dialog_buttons_inside_screen(self):
        self.app.show_dialog("Long text", "Long message. " * 200, ("Cancel", "Yes", "No"))
        for width, height in ((79, 31), (45, 15), (109, 36)):
            self.app.width, self.app.height = width, height
            self.app.render()
            dialog = self.app.dialog
            self.assertGreaterEqual(dialog.x, 0)
            self.assertGreaterEqual(dialog.y, 0)
            self.assertLessEqual(dialog.x + dialog.width, width)
            self.assertLessEqual(dialog.y + dialog.height, height)
            for button in dialog.buttons:
                self.assertLessEqual(button.x + button.width, dialog.x + dialog.width)
                self.assertLess(button.y + button.height, dialog.y + dialog.height)


@unittest.skipUnless(os.name == "nt", "Windows mouse record layout")
class WheelDecoderTests(unittest.TestCase):
    def test_signed_precision_wheel_coordinates_and_double_click(self):
        decoder = Decoder()
        record = InputRecord()
        record.kind = 2
        mouse = record.data.mouse
        mouse.flags = 4
        mouse.position.x, mouse.position.y = 8, 10
        mouse.buttons = (60 & 0xFFFF) << 16
        self.assertEqual(decoder.decode(record), [])
        event = decoder.decode(record, (2, 3))[0]
        self.assertEqual((event.kind, event.delta, event.x, event.y), ("scroll", -1, 6, 7))
        mouse.buttons = (-240 & 0xFFFF) << 16
        self.assertEqual(decoder.decode(record)[0].delta, 2)
        mouse.flags, mouse.buttons = 2, 1
        event = decoder.decode(record)[0]
        self.assertEqual((event.kind, event.clicks), ("down", 2))


if __name__ == "__main__":
    unittest.main()
