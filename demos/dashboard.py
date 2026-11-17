"""Run with: python -m demos.dashboard. Everything displayed is local, simulated demo data."""


# Allow both `python FILE.py` here and `python -m demos.NAME` from the root.
if not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"

from collections import deque
from datetime import datetime
import math
import time

from cellkit import App, Button, Checkbox, Label, Panel, ProgressBar, TextInput, Theme, Widget


class ActivityChart(Widget):
    """Example custom widget: a small rolling character-cell chart."""

    def __init__(self):
        super().__init__(0, 0, 30, 5)
        self.samples = deque([0.0] * 100, maxlen=100)

    def draw(self, canvas):
        values = list(self.samples)[-self.width:]
        for x, value in enumerate(values):
            filled = round(value * self.height)
            for y in range(self.height):
                active = y >= self.height - filled
                canvas.text(self.x + x, self.y + y, "│" if active else "·",
                            Theme.accent if active else Theme.border)


class Dashboard:
    def __init__(self):
        self.app = App(min_width=79, min_height=31)
        self.started_at = time.monotonic()
        self.running = False
        self.finished = 0
        self.job_progress = 0.0
        self.chart_elapsed = 0.0
        self.jobs = deque(["Validate inputs", "Build report", "Package results"])
        self.messages = deque(maxlen=5)
        add = self.app.add

        self.heading = add(Label(2, 1, "N O R T H S T A R   /   OPERATIONS", 45, Theme.accent))
        self.clock = add(Label(0, 1, "", 20, Theme.muted))
        self.subtitle = add(Label(2, 2, "Python standard library only  /  interactive terminal workspace", 75, Theme.muted))
        self.metrics = [add(Panel(0, 4, 20, 5, name)) for name in
                        ("ENGINE", "COMPLETED", "MOUSE CLICKS", "UPTIME")]
        self.metric_values = [add(Label(0, 6, "", 15, Theme.accent)) for _ in self.metrics]

        self.queue_panel = add(Panel(0, 10, 40, 13, "01  JOB CONTROL"))
        self.signal_panel = add(Panel(0, 10, 30, 13, "02  LIVE SIGNAL"))
        self.log_panel = add(Panel(0, 24, 70, 6, "03  ACTIVITY"))
        self.current = add(Label(0, 12, "", 30, Theme.accent))
        self.progress = add(ProgressBar(0, 14, 30))
        self.queue_label = add(Label(0, 16, "", 30, Theme.muted))
        self.name = add(TextInput(0, 17, 25, placeholder="Name a new job...", max_length=40))
        self.add_button = add(Button(0, 17, "+ Add", self.add_job, width=9))
        self.start_button = add(Button(0, 20, "Start", self.toggle, width=11))
        self.reset_button = add(Button(0, 20, "Reset", self.reset, width=11))
        self.fast = add(Checkbox(0, 12, "Fast processing", on_change=self.speed_changed))
        self.chart = add(ActivityChart())
        self.signal_label = add(Label(0, 20, "SIMULATED THROUGHPUT", 30, Theme.muted))
        self.click_button = add(Button(0, 21, "Click test: 0", self.click_test, width=19))
        self.test_clicks = 0
        self.quit_button = add(Button(0, 21, "Exit", self.app.stop, width=8))
        self.log_labels = [add(Label(0, 25 + i, "", 70, Theme.muted)) for i in range(4)]
        self.footer = add(Label(2, 30, "CLICK to interact   TAB / SHIFT+TAB to move   ENTER to press   ESC to exit", 90, Theme.muted))

        self.app.on_resize = self.layout
        self.app.on_tick = self.tick
        self.app.set_focus(self.start_button)
        self.log("Ready. Press Start, or try the mouse-click test.")

    def log(self, message):
        self.messages.append(datetime.now().strftime("%H:%M:%S") + "  " + message)

    def toggle(self):
        if not self.jobs:
            self.log("Queue empty. Add another job to continue.")
            return
        self.running = not self.running
        self.log("Processing started." if self.running else "Processing paused.")
        self.start_button.flash()
        self.app.notify("Processing started." if self.running else "Processing paused.")

    def reset(self):
        self.running = False
        self.finished = 0
        self.job_progress = 0.0
        self.jobs = deque(["Validate inputs", "Build report", "Package results"])
        self.chart.samples = deque([0.0] * 100, maxlen=100)
        self.log("Demo queue restored. Ready for another run.")
        self.reset_button.flash()
        self.app.notify("Demo queue restored.")

    def add_job(self):
        name = self.name.value.strip()
        if not name:
            self.log("Enter a job name first.")
            self.app.set_focus(self.name)
            self.name.flash(style=Theme.warning)
            self.app.notify("Enter a job name first.", kind="warning")
            return
        self.jobs.append(name)
        self.name.value, self.name.cursor = "", 0
        self.log("Queued: " + name)
        self.add_button.flash()
        self.app.notify("Queued: " + name, kind="success")

    def speed_changed(self, checked):
        self.log("Processing speed: " + ("fast (2.5x)." if checked else "normal."))

    def click_test(self):
        self.test_clicks += 1
        self.click_button.text = f"Click test: {self.test_clicks}"
        self.log(f"Test button activated {self.test_clicks} time(s).")
        self.click_button.flash(duration=2.4)
        kinds = ("info", "success", "warning", "error")
        kind = kinds[(self.test_clicks - 1) % len(kinds)]
        self.app.notify(f"Example {kind} toast. Click to dismiss, or wait 3 seconds.", kind=kind)

    def layout(self, width, height):
        margin, gap = 2, 2
        usable = width - margin * 2
        card_width = (usable - gap * 3) // 4
        for i, (panel, value) in enumerate(zip(self.metrics, self.metric_values)):
            x = margin + i * (card_width + gap)
            panel.bounds(x, 4, card_width, 5)
            value.bounds(x + 2, 6, card_width - 4)
        self.clock.bounds(width - 22, 1, 20)
        left_width = (usable - gap) * 56 // 100
        right_x = margin + left_width + gap
        right_width = usable - left_width - gap
        self.queue_panel.bounds(margin, 10, left_width, 14)
        self.signal_panel.bounds(right_x, 10, right_width, 14)
        lx, rx = margin + 2, right_x + 2
        inner_left, inner_right = left_width - 4, right_width - 4
        self.current.bounds(lx, 12, inner_left)
        self.progress.bounds(lx, 14, inner_left)
        self.queue_label.bounds(lx, 16, inner_left)
        self.name.bounds(lx, 17, inner_left - 10)
        self.add_button.bounds(lx + inner_left - 9, 17, 9)
        self.start_button.bounds(lx, 20, 11)
        self.reset_button.bounds(lx + 13, 20, 11)
        self.fast.bounds(rx, 12, inner_right)
        self.chart.bounds(rx, 14, inner_right, 5)
        self.signal_label.bounds(rx, 19, inner_right)
        self.click_button.bounds(rx, 20, inner_right - 9)
        self.quit_button.bounds(rx + inner_right - 8, 20, 8)
        self.log_panel.bounds(margin, 25, usable, height - 27)
        available_logs = min(4, height - 29)
        for i, label in enumerate(self.log_labels):
            label.visible = i < available_logs
            label.bounds(margin + 2, 26 + i, usable - 4)
        self.footer.bounds(margin, height - 1, usable)

    def tick(self, seconds):
        elapsed = time.monotonic() - self.started_at
        if self.running and self.jobs:
            self.job_progress += seconds * (0.30 if self.fast.checked else 0.12)
            if self.job_progress >= 1:
                self.log("Finished: " + self.jobs.popleft())
                self.finished += 1
                self.job_progress = 0.0
                if not self.jobs:
                    self.running = False
                    self.log("All jobs complete. Add a job or reset the demo.")
                    self.metric_values[1].flash(duration=3)
                    self.app.notify("All jobs completed successfully!", kind="success", duration=4)
        self.chart_elapsed += seconds
        if self.chart_elapsed >= 0.15:
            signal = 0.55 + 0.22 * math.sin(elapsed * 2) + 0.13 * math.sin(elapsed * 5)
            self.chart.samples.append(signal if self.running else 0.0)
            self.chart_elapsed = 0.0
        status = "RUNNING" if self.running else ("READY" if self.jobs else "COMPLETE")
        values = ("● " + status, f"{self.finished:02d} jobs", f"{self.app.mouse_clicks:03d} clicks",
                  f"{int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}")
        for label, value in zip(self.metric_values, values):
            label.text = value
        self.clock.text = datetime.now().strftime("%a  %H:%M:%S")
        self.current.text = self.jobs[0] if self.jobs else "All clear. Nice work."
        self.progress.value = self.job_progress if self.jobs else 1.0
        self.queue_label.text = f"{len(self.jobs)} queued  /  " + ("2.5x speed" if self.fast.checked else "normal speed")
        self.start_button.text = "Pause" if self.running else "Start"
        self.start_button.enabled = bool(self.jobs)
        visible_labels = [label for label in self.log_labels if label.visible]
        recent = list(self.messages)[-len(visible_labels):] if visible_labels else []
        for i, label in enumerate(visible_labels):
            label.text = recent[i] if i < len(recent) else ""

    def run(self):
        self.app.run()


if __name__ == "__main__":
    try:
        Dashboard().run()
    except (RuntimeError, OSError) as error:
        raise SystemExit(f"CellKit: {error}") from None
