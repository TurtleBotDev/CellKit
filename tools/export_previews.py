"""Export actual demo cell grids with synthetic data for documentation images.

Run from the repository root: python -m tools.export_previews
Then: powershell -NoProfile -File tools/render_previews.ps1
"""

from collections import deque
import json
import math
from pathlib import Path
import time

from demos.dashboard import Dashboard
from demos.maze import MazeDemo, apply_palette
from demos.sample_data import sample_browser


def export():
    frames = []

    def prepare(demo):
        demo.app.width, demo.app.height = 109, 36
        demo.layout(109, 36)

    def capture(demo, name, title):
        frames.append({"name": name, "title": title, "rows": demo.app.render().rows})

    apply_palette("ocean")
    dashboard = Dashboard()
    prepare(dashboard)
    dashboard.started_at = time.monotonic() - 83
    dashboard.running, dashboard.finished, dashboard.job_progress = True, 7, 0.63
    dashboard.messages = deque(["14:32:12  Finished: Validate inputs",
                                 "14:32:14  Queued: Weekly summary",
                                 "14:32:16  Processing started."], maxlen=5)
    dashboard.chart.samples = deque([0.55 + 0.25 * math.sin(i * 0.42) for i in range(100)], maxlen=100)
    dashboard.tick(0)
    dashboard.clock.text = "Tue  14:32:18"
    capture(dashboard, "dashboard", "Operations dashboard")
    dashboard.click_button.flash(style="1;38;2;255;255;255;48;2;180;35;45")
    dashboard.app.notify("Report ready. Click a notification to dismiss it.", kind="success")
    dashboard.app.notify("Custom flash colour: white text on red.", kind="error")
    capture(dashboard, "effects", "Toasts and coloured flashes")

    apply_palette("violet")
    maze = MazeDemo()
    prepare(maze)
    maze.model.algorithm = "A*"
    maze.model.reset_search()
    while maze.model.state not in ("found", "no route"):
        maze.model.step()
    maze.tick(0)
    capture(maze, "maze-violet", "Maze lab / violet theme")
    apply_palette("amber")
    amber = MazeDemo()
    prepare(amber)
    amber.model = maze.model
    amber.board.model = amber.model
    amber.tick(0)
    capture(amber, "maze-amber", "Maze lab / amber theme")

    apply_palette("ocean")
    browser = sample_browser()
    prepare(browser)
    browser.table.select(8)
    browser.tick(0)
    capture(browser, "files", "File explorer / sample data")
    browser.app.show_dialog("File details",
        "C:/Projects/CellKit/reports/monthly.csv\n\nType: CSV report\nSize: 24.5 KB\n"
        "Modified: 2026-11-17 14:32:00\n\nThis preview uses sample data.", ("Close", "Preview"))
    capture(browser, "dialog", "Modal dialog and focus")

    output = Path(__file__).resolve().parents[1] / ".test-results" / "previews"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "frames.json"
    path.write_text(json.dumps(frames, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(frames)} demo frames to {path}")


if __name__ == "__main__":
    export()
