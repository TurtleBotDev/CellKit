"""Hands-free recording: python -m demos.background (60-second loop, Esc exits).

All changes are simulated. The file-browser scene uses synthetic data.
Use --once to exit after one loop. The real mouse is not moved or controlled.
"""


# Allow both `python FILE.py` here and `python -m demos.NAME` from the root.
if not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"

import argparse

from cellkit import App, Theme
from .dashboard import Dashboard
from .maze import MazeDemo, apply_palette
from .sample_data import sample_browser


class Showcase(App):
    SCENE_SECONDS = 20

    def __init__(self, once=False):
        super().__init__(min_width=79, min_height=31)
        self.once = once
        self.scene_index = -1
        self.scene_time = 0.0
        self.scene = None
        self.actions = []
        self.on_tick = self.advance
        self.next_scene()

    def next_scene(self):
        self.close_dialog()
        self.cancel_press()
        self.set_focus(None)
        self.toasts.items.clear()
        self.scene_index = (self.scene_index + 1) % 3
        self.scene_time = 0.0
        apply_palette(("ocean", "violet", "amber")[self.scene_index])
        self.scene = (Dashboard, MazeDemo, sample_browser)[self.scene_index]()
        self.widgets = self.scene.app.widgets
        self.scene.app = self
        self.on_resize = self.scene.layout
        if self.width >= self.min_width and self.height >= self.min_height:
            self.scene.layout(self.width, self.height)
        self.actions = self.make_actions()
        self.set_focus((self.scene.start_button if self.scene_index == 0 else
                        self.scene.board if self.scene_index == 1 else self.scene.table))

    def make_actions(self):
        ui = self.scene
        if self.scene_index == 0:
            red = "1;38;2;255;255;255;48;2;180;35;45"
            return [
                (0.4, lambda: self.notify("CellKit: standard-library Python, no pip installs.", duration=3)),
                (1.0, ui.toggle),
                (2.0, lambda: self.set_focus(ui.name)),
                (4.0, ui.add_job),
                (4.5, ui.fast.activate),
                (6.0, ui.click_test),
                (8.0, lambda: ui.reset_button.flash(duration=2, style=red)),
                (8.0, lambda: self.notify("Custom flash colour: white text on red.", kind="error")),
                (11.0, lambda: self.set_focus(ui.start_button)),
                (15.0, lambda: self.show_dialog("A working interface, in a terminal",
                    "Buttons, fields, checkboxes, charts, progress and notifications.\n\n"
                    "This dialog takes focus while the background job keeps moving.", ("Continue",))),
                (17.5, self.close_dialog),
            ]
        if self.scene_index == 1:
            return [
                (1.0, ui.toggle_run),
                (3.0, lambda: self.notify("A custom widget draws the entire maze.", duration=2)),
                (4.0, lambda: setattr(ui, "running", False)),
                (4.3, ui.single_step),
                (4.7, ui.single_step),
                (5.2, ui.toggle_run),
                (11.0, ui.switch_algorithm),
                (11.5, ui.toggle_run),
                (15.0, lambda: setattr(ui.fast, "checked", True)),
            ]
        return [
            (1.0, lambda: ui.table.scroll(5)),
            (2.0, lambda: ui.table.select(10)),
            (3.0, lambda: ui.table.scroll(6)),
            (4.0, lambda: self.show_dialog("Sample file details",
                "C:/Projects/CellKit/reports/monthly.csv\n\nType: CSV report\n"
                "Size: 24.5 KB\nStatus: ready\n\nAll filenames in this recording are sample data.", ("Close",))),
            (6.0, self.close_dialog),
            (6.5, lambda: self.set_focus(ui.filter)),
            (9.0, lambda: self.set_filter("")),
            (10.0, ui.cycle_sort),
            (10.5, lambda: self.set_focus(ui.table)),
            (11.0, lambda: ui.table.select(20)),
            (12.0, lambda: self.show_dialog("Confirmation dialog",
                "Callbacks receive your choice after focus returns to the application.",
                ("Cancel", "Continue"), lambda result: self.notify("Confirmed automatically.", kind="success"))),
            (13.5, lambda: self.set_focus(self.dialog.buttons[1]) if self.dialog else None),
            (14.0, lambda: self.close_dialog("Continue")),
            (16.0, lambda: self.notify("Notifications stack and expire automatically.", kind="info")),
            (17.0, lambda: ui.sort_button.flash(duration=2)),
        ]

    def set_filter(self, text):
        self.scene.filter.value = text
        self.scene.filter.cursor = len(text)

    def advance(self, seconds):
        self.scene_time += seconds
        if self.scene_time >= self.SCENE_SECONDS:
            if self.once and self.scene_index == 2:
                self.stop()
                return
            self.next_scene()
        if self.scene_index == 0 and 2 <= self.scene_time < 4:
            text = "Weekly summary"[:int((self.scene_time - 2) * 9)]
            self.scene.name.value, self.scene.name.cursor = text, len(text)
        elif self.scene_index == 2 and 6.5 <= self.scene_time < 9:
            self.set_filter("report_1"[:int((self.scene_time - 6.5) * 5)])
        while self.actions and self.actions[0][0] <= self.scene_time:
            _, action = self.actions.pop(0)
            action()
        self.scene.tick(seconds)
        title = ("Dashboard / ocean", "Maze / violet", "File browser / amber")[self.scene_index]
        self.scene.footer.text = f"AUTOPLAY {self.scene_index + 1}/3  |  {title}  |  {self.scene_time:02.0f}/20s  |  Esc: exit"

    def dispatch(self, event):
        # Ignore interaction during recording, except resize/focus changes and exit.
        if event.kind == "key" and event.key in ("escape", "quit"):
            self.stop()
        elif event.kind in ("resize", "blur"):
            super().dispatch(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hands-free CellKit showcase")
    parser.add_argument("--once", action="store_true", help="exit after one 60-second loop")
    options = parser.parse_args()
    try:
        Showcase(once=options.once).run()
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"CellKit: {error}") from None
