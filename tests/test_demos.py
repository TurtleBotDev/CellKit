from pathlib import Path
import subprocess
import sys
import unittest

from cellkit import Theme
from demos.background import Showcase
from demos.maze import MazeBoard


class ShowcaseTests(unittest.TestCase):
    def setUp(self):
        # Theme selection is process-wide; keep these checks independent of others.
        self.saved = [(owner, name, value) for owner in (Theme, MazeBoard)
                      for name, value in vars(owner).items()
                      if not name.startswith('_') and isinstance(value, str)]

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_automatic_scenes_complete_and_once_exits(self):
        app = Showcase(once=True)
        app.width, app.height, app.running = 109, 36, True
        app.on_resize(app.width, app.height)
        seen = set()
        for _ in range(245):
            app.update(0.25)
            seen.add(app.scene_index)
            app.render()
            if not app.running:
                break
        self.assertEqual(seen, {0, 1, 2})
        self.assertFalse(app.running)

    def test_default_mode_repeats(self):
        app = Showcase()
        app.width, app.height, app.running = 79, 31, True
        app.on_resize(app.width, app.height)
        for _ in range(244):
            app.update(0.25)
        self.assertTrue(app.running)
        self.assertEqual(app.scene_index, 0)
        app.render()

    def test_demo_scripts_import_from_inside_demos_folder(self):
        folder = Path(__file__).resolve().parents[1] / "demos"
        source = ("import runpy; "
                  "[runpy.run_path(name + '.py', run_name='import_check') "
                  "for name in ('background', 'dashboard', 'maze', 'files', 'hello')]")
        result = subprocess.run([sys.executable, "-c", source], cwd=folder,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
