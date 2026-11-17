"""Read-only file browser: python -m demos.files [folder]. Standard library only."""


# Allow both `python FILE.py` here and `python -m demos.NAME` from the root.
if not __package__:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import stat

from cellkit import App, Button, Label, ListBox, Table, TextInput, Theme


@dataclass
class FileEntry:
    path: Path
    folder: bool
    size: int
    modified: float


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


class FileBrowser:
    def __init__(self, folder=None):
        self.app = App(min_width=79, min_height=31)
        self.directory = Path(folder or Path.cwd()).resolve()
        self.history = []
        self.entries, self.shown = [], []
        self.sort_mode = 0
        self.last_filter = ""
        self.scan_note = ""
        add = self.app.add
        add(Label(2, 1, "F I E L D N O T E S   /   FILE EXPLORER", 65, Theme.accent))
        add(Label(2, 2, "Browse, filter and inspect  /  read-only", 65, Theme.muted))
        self.path_label = add(Label(2, 3, "", 75))
        self.back_button = add(Button(2, 5, "Back", self.back, width=9))
        self.up_button = add(Button(12, 5, "Up", self.up, width=7))
        self.open_button = add(Button(20, 5, "Open", self.open_selected, width=9))
        self.details_button = add(Button(30, 5, "Details", self.details, width=11))
        self.refresh_button = add(Button(42, 5, "Refresh", self.refresh, width=11))
        self.sort_button = add(Button(54, 5, "Sort:name", self.cycle_sort, width=11))
        add(Button(66, 5, "Help", self.help, width=11))
        add(Label(2, 9, "Filter names:", 19, Theme.muted))
        self.filter = add(TextInput(23, 8, 54, placeholder="Type to filter this folder...", max_length=80))
        self.place_paths = [self.directory, Path.home(), Path(self.directory.anchor), Path(os.__file__).parent]
        self.places = add(ListBox(2, 12, 19, 10,
                                  ["Start folder", "Home", "Drive root", "Python library"],
                                  title="PLACES", on_activate=self.open_place))
        self.table = add(Table(23, 12, 54, 15,
                               [("Name", 16), ("Type", 6), ("Size", 8), ("Modified", 12)],
                               title="CONTENTS", on_select=self.selected_changed,
                               on_activate=lambda index: self.open_selected()))
        self.tip = add(Label(2, 24, "Enter opens", 19, Theme.muted))
        self.selection_label = add(Label(2, 28, "", 75))
        self.status = add(Label(2, 29, "", 75, Theme.muted))
        self.footer = add(Label(2, 30, "Wheel: scroll | Click: select | Enter/double-click: open | Esc: exit", 75, Theme.muted))
        self.app.on_resize = self.layout
        self.app.on_tick = self.tick
        self.load_directory(self.directory, remember=False)
        if self.app.dialog is None:
            self.app.set_focus(self.table)

    def error(self, message):
        self.app.show_dialog("Could not open", str(message))

    def load_directory(self, folder, remember=True):
        """Build the next listing first; a failed scan leaves the old view intact."""
        entries = []
        skipped, limited = 0, False
        try:
            folder = Path(folder).resolve()
            with os.scandir(folder) as scan:
                for index, item in enumerate(scan):
                    if index >= 2000:
                        limited = True
                        break
                    try:
                        info = item.stat()
                        entries.append(FileEntry(Path(item.path), stat.S_ISDIR(info.st_mode),
                                                 info.st_size, info.st_mtime))
                    except OSError:
                        skipped += 1
        except (OSError, RuntimeError) as error:
            self.error(error)
            return False
        if remember and folder != self.directory:
            self.history.append(self.directory)
        self.directory, self.entries = folder, entries
        self.filter.value, self.filter.cursor, self.last_filter = "", 0, ""
        notes = (["limited to first 2,000 entries"] if limited else [])
        if skipped:
            notes.append(f"{skipped} unavailable entries skipped")
        self.scan_note = " / ".join(notes)
        self.apply_filter()
        self.app.set_focus(self.table)
        return True

    def apply_filter(self):
        query = self.filter.value.casefold()
        self.shown = [entry for entry in self.entries if query in entry.path.name.casefold()]
        def order(entry):
            value = (entry.path.name.casefold(), -entry.size, -entry.modified)[self.sort_mode]
            return (not entry.folder, value, entry.path.name.casefold())
        self.shown.sort(key=order)
        self.table.set_rows([
            (entry.path.name, "Folder" if entry.folder else "File",
             "--" if entry.folder else human_size(entry.size),
             datetime.fromtimestamp(entry.modified).strftime("%d %b %Y"))
            for entry in self.shown
        ])
        self.status.text = f"{len(self.shown)} shown / {len(self.entries)} loaded  |  Read-only"
        if self.scan_note:
            self.status.text += "  |  " + self.scan_note

    def selected_entry(self):
        return self.shown[self.table.selected] if self.table.selected is not None else None

    def selected_changed(self, index):
        entry = self.selected_entry()
        self.selection_label.text = ("Selected: " + entry.path.name) if entry else "No matching entries."
        self.open_button.enabled = self.details_button.enabled = entry is not None

    def open_selected(self):
        entry = self.selected_entry()
        if entry:
            if entry.folder:
                self.load_directory(entry.path)
            else:
                self.details()

    def open_place(self, index):
        self.load_directory(self.place_paths[index])

    def back(self):
        if self.history and self.load_directory(self.history[-1], remember=False):
            self.history.pop()

    def up(self):
        self.load_directory(self.directory.parent)

    def refresh(self):
        if self.load_directory(self.directory, remember=False):
            self.refresh_button.flash()
            self.app.notify("Folder refreshed.", kind="success")

    def cycle_sort(self):
        self.sort_mode = (self.sort_mode + 1) % 3
        self.sort_button.text = "Sort:" + ("name", "size", "date")[self.sort_mode]
        self.apply_filter()

    def details(self):
        entry = self.selected_entry()
        if entry is None:
            return
        try:
            info = entry.path.stat()
        except OSError as error:
            self.error(error)
            return
        message = (f"{entry.path}\n\n"
                   f"Type: {'Folder' if entry.folder else 'File'}\n"
                   f"Size: {'--' if entry.folder else human_size(info.st_size)}\n"
                   f"Modified: {datetime.fromtimestamp(info.st_mtime):%Y-%m-%d %H:%M:%S}")
        buttons = ("Close", "Preview") if stat.S_ISREG(info.st_mode) else ("Close",)
        self.app.show_dialog("File details", message, buttons=buttons,
                             on_result=lambda result: self.preview(entry.path) if result == "Preview" else None)

    def preview(self, path):
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                raise OSError("Preview supports regular files only.")
            with path.open("rb") as source:
                data = source.read(4096)
        except OSError as error:
            self.error(error)
            return
        if b"\0" in data:
            message = "This appears to be binary data. Text preview is not available."
        else:
            message = "First 4 KiB (text may be shortened to fit):\n\n" + data.decode("utf-8", errors="replace")
        self.app.show_dialog("Preview: " + path.name, message)

    def help(self):
        self.app.show_dialog("Using Fieldnotes",
                             "Click a row to select it. Enter or double-click opens folders; "
                             "files show their details. Preview reads a small text excerpt.\n\n"
                             "Scroll with the mouse wheel or drag the scrollbar. Use arrows, "
                             "Page Up/Down, Home and End with the table focused.\n\n"
                             "Back retraces folder history. Up opens the parent. Type in the "
                             "filter to match names. Sorting keeps folders first.\n\n"
                             "Tab moves focus. Esc closes a dialog, or exits the app. "
                             "This demo never edits, deletes, or launches files.")

    def layout(self, width, height):
        self.path_label.bounds(2, 3, width - 4)
        self.filter.bounds(23, 8, width - 25)
        self.table.bounds(23, 12, width - 25, height - 16)
        self.table.columns[0] = ("Name", width - 63)
        self.places.bounds(2, 12, 19, min(10, height - 16))
        self.tip.bounds(2, height - 7, 19)
        self.selection_label.bounds(2, height - 3, width - 4)
        self.status.bounds(2, height - 2, width - 4)
        self.footer.bounds(2, height - 1, width - 4)

    def tick(self, seconds):
        if self.filter.value != self.last_filter:
            self.last_filter = self.filter.value
            self.apply_filter()
        self.path_label.text = str(self.directory)
        self.back_button.enabled = bool(self.history)
        self.up_button.enabled = self.directory.parent != self.directory

    def run(self):
        self.app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only CellKit file browser")
    parser.add_argument("folder", nargs="?", default=".", help="starting folder (default: current folder)")
    options = parser.parse_args()
    try:
        FileBrowser(options.folder).run()
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"CellKit: {error}") from None
