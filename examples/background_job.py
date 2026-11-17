"""Cooperative background work: python -m examples.background_job"""

from queue import Empty, Queue
from threading import Event, Thread

from cellkit import App, Button, Label, Panel, ProgressBar, Theme


class BackgroundJob:
    def __init__(self):
        self.app = App(min_width=60, min_height=20)
        self.messages = Queue()
        self.cancel = Event()
        self.worker = None
        self.busy = False
        self.app.add(Panel(2, 1, 56, 16, "Background worker"))
        self.status = self.app.add(Label(5, 4, "Ready. Start a simulated job.", width=50))
        self.progress = self.app.add(ProgressBar(5, 7, 48))
        self.start_button = self.app.add(Button(5, 10, "Start", self.start, width=12))
        self.cancel_button = self.app.add(Button(20, 10, "Cancel", self.cancel.set, width=12))
        self.cancel_button.enabled = False
        self.app.add(Button(35, 10, "Exit", self.app.stop, width=12))
        self.app.add(Label(2, 18, "The UI stays responsive while a worker runs.", width=56, style=Theme.muted))
        self.app.on_tick = self.poll
        self.app.set_focus(self.start_button)

    def start(self):
        if self.busy:
            return
        self.busy = True
        self.cancel.clear()
        self.start_button.enabled, self.cancel_button.enabled = False, True
        self.progress.value = 0
        self.status.text = "Working..."
        self.worker = Thread(target=self.work, daemon=True)
        self.worker.start()

    def work(self):
        # Only queue messages here. Widget changes belong in poll(), on the UI thread.
        try:
            for step in range(1, 41):
                if self.cancel.wait(0.05):  # Simulated work, with prompt cancellation.
                    self.messages.put(("done", "Cancelled"))
                    return
                self.messages.put(("progress", step / 40))
            self.messages.put(("done", "Complete"))
        except Exception as error:
            self.messages.put(("error", str(error)))

    def poll(self, seconds):
        # A bounded batch prevents a busy producer monopolising the UI loop.
        for _ in range(64):
            try:
                kind, value = self.messages.get_nowait()
            except Empty:
                break
            if kind == "progress":
                self.progress.value = value
            else:
                self.busy = False
                self.start_button.enabled, self.cancel_button.enabled = True, False
                self.status.text = value
                self.app.notify(value, kind="error" if kind == "error" else "info")

    def run(self):
        try:
            self.app.run()
        finally:
            self.cancel.set()
            if self.worker:
                self.worker.join(timeout=1)


if __name__ == "__main__":
    BackgroundJob().run()
