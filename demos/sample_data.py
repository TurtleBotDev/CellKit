"""Synthetic file listings for recordings and documentation images."""

from pathlib import Path
import tempfile

from .files import FileBrowser, FileEntry


def sample_browser():
    # Initialise the browser in an empty directory, then replace its model in memory.
    with tempfile.TemporaryDirectory(prefix="cellkit-preview-") as folder:
        browser = FileBrowser(folder)
    root = Path("C:/Projects/CellKit")
    browser.directory = root
    names = ["assets", "docs", "reports", "tests", "README.md", "settings.json"]
    names += [f"report_{number:02d}.csv" for number in range(1, 26)]
    browser.entries = [FileEntry(root / name, index < 4, 800 + index * 1837,
                                 1794873600 + index * 600) for index, name in enumerate(names)]
    browser.apply_filter()
    return browser
