"""Launch native tests in their own hidden console, never the user's terminal."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name == "nt", "Requires Windows console APIs")
class ConsoleIntegrationTests(unittest.TestCase):
    def test_real_console_input_output_and_cleanup(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "tests" / "console_probe.py")],
            cwd=root, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NATIVE CONSOLE PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
