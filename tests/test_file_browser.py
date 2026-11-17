from pathlib import Path
import tempfile
import unittest

from demos.files import FileBrowser


class FileBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / "folder").mkdir()
        (self.root / "hello.txt").write_text("Hello from the preview!", encoding="utf-8")
        (self.root / "binary.bin").write_bytes(b"\0\1\2")
        self.browser = FileBrowser(self.root)
        self.browser.app.width, self.browser.app.height = 79, 31
        self.browser.layout(79, 31)

    def test_navigation_back_and_failed_directory_preserve_listing(self):
        browser = self.browser
        self.assertTrue(browser.shown[0].folder)
        browser.open_selected()
        self.assertEqual(browser.directory, self.root / "folder")
        self.assertEqual(browser.history, [self.root])
        browser.back()
        self.assertEqual(browser.directory, self.root)
        self.assertEqual(browser.history, [])
        previous = list(browser.shown)
        self.assertFalse(browser.load_directory(self.root / "missing"))
        self.assertEqual(browser.shown, previous)
        self.assertEqual(browser.directory, self.root)
        self.assertIsNotNone(browser.app.dialog)

    def test_filter_details_preview_and_escape_have_no_file_writes(self):
        browser = self.browser
        original = (self.root / "hello.txt").read_bytes()
        browser.filter.value = "HELLO"
        browser.tick(0)
        self.assertEqual([entry.path.name for entry in browser.shown], ["hello.txt"])
        browser.details()
        self.assertIn("hello.txt", browser.app.dialog.message)
        browser.app.close_dialog("Preview")
        self.assertIn("Hello from the preview!", browser.app.dialog.message)
        browser.app.close_dialog()
        self.assertEqual((self.root / "hello.txt").read_bytes(), original)
        browser.filter.value = "no match"
        browser.tick(0)
        self.assertIsNone(browser.table.selected)
        self.assertFalse(browser.open_button.enabled)

    def test_binary_preview_and_layout(self):
        browser = self.browser
        browser.preview(self.root / "binary.bin")
        self.assertIn("binary", browser.app.dialog.message)
        browser.app.close_dialog()
        for width, height in ((79, 31), (109, 36)):
            browser.layout(width, height)
            for widget in browser.app.widgets:
                self.assertGreaterEqual(widget.x, 0)
                self.assertGreaterEqual(widget.y, 0)
                self.assertLessEqual(widget.x + widget.width, width)
                self.assertLessEqual(widget.y + widget.height, height)


if __name__ == "__main__":
    unittest.main()
