"""Internal integration probe. Run via test_console.py, not in your open shell.

WriteConsoleInputW inserts synthetic OS records into THIS process's console.
It does not move the system pointer or automate another application's window.
"""

import ctypes as ct
from ctypes import wintypes as wt
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cellkit import App, Button, Label, TextInput, Table
from cellkit.terminal import Coord, InputRecord, Terminal


def main():
    terminal = Terminal()
    api = terminal.api
    api.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, wt.LPVOID,
                                wt.DWORD, wt.DWORD, wt.HANDLE]
    api.CreateFileW.restype = wt.HANDLE
    api.SetStdHandle.argtypes = [wt.DWORD, wt.HANDLE]
    api.SetStdHandle.restype = wt.BOOL
    api.WriteConsoleInputW.argtypes = [wt.HANDLE, ct.POINTER(InputRecord), wt.DWORD,
                                      ct.POINTER(wt.DWORD)]
    api.WriteConsoleInputW.restype = wt.BOOL
    api.ReadConsoleOutputCharacterW.argtypes = [wt.HANDLE, wt.LPWSTR, wt.DWORD,
                                               Coord, ct.POINTER(wt.DWORD)]
    api.ReadConsoleOutputCharacterW.restype = wt.BOOL
    # subprocess stdout/stderr are pipes; obtain the hidden console's own handles.
    input_handle = api.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)
    output_handle = api.CreateFileW("CONOUT$", 0xC0000000, 3, None, 3, 0, None)
    assert input_handle != wt.HANDLE(-1).value, ct.WinError(ct.get_last_error())
    assert output_handle != wt.HANDLE(-1).value, ct.WinError(ct.get_last_error())
    terminal.check(api.SetStdHandle(-10, input_handle))
    terminal.check(api.SetStdHandle(-11, output_handle))

    def mode(handle):
        value = wt.DWORD()
        terminal.check(api.GetConsoleMode(handle, ct.byref(value)))
        return value.value

    def push(records):
        array = (InputRecord * len(records))(*records)
        written = wt.DWORD()
        terminal.check(api.WriteConsoleInputW(input_handle, array, len(array), ct.byref(written)))
        assert written.value == len(array)

    def mouse(x, y, buttons):
        record = InputRecord()
        record.kind = 2
        record.data.mouse.position = Coord(x, y)
        record.data.mouse.buttons = buttons
        return record

    def key(code, char="\0"):
        record = InputRecord()
        record.kind = 1
        record.data.key.down = True
        record.data.key.repeat = 1
        record.data.key.code, record.data.key.char = code, char
        return record

    before = (mode(input_handle), mode(output_handle))
    app = App(min_width=50, min_height=20)
    status = app.add(Label(1, 1, "Waiting", width=20))
    calls = []

    def clicked():
        calls.append("clicked")
        status.text = "Clicked!"

    app.add(Button(2, 3, "Test", clicked, width=12))
    field = app.add(TextInput(2, 7, 20))
    answers = []
    table = app.add(Table(2, 11, 48, 8, [("Name", 30)], [(f"Row {i}",) for i in range(20)],
                          on_activate=lambda index: app.show_dialog("Confirm", "Selected row " + str(index),
                                                                    ("Cancel", "Yes"), answers.append)))
    stage = 0
    started = time.monotonic()

    def tick(seconds):
        nonlocal stage
        assert time.monotonic() - started < 5, "App did not process injected console events"
        if stage == 0:
            assert mode(input_handle) & 0x10  # mouse enabled
            assert not mode(input_handle) & 0x40  # quick-edit disabled
            push([mouse(4, 4, 1), mouse(4, 4, 0), key(9, "\t"), key(65, "A")])
            stage = 1
        elif stage == 1 and calls and field.value == "A":
            # The next frame will draw the callback's updated label.
            stage = 2
        elif stage == 2:
            buffer = ct.create_unicode_buffer(8)
            read = wt.DWORD()
            terminal.check(api.ReadConsoleOutputCharacterW(output_handle, buffer, 8,
                                                           Coord(1, 1), ct.byref(read)))
            assert buffer.value == "Clicked!", repr(buffer.value)
            wheel = mouse(4, 14, (-120 & 0xFFFF) << 16)
            wheel.data.mouse.flags = 4
            push([wheel, mouse(4, 13, 1), mouse(4, 13, 0), key(13, "\r")])
            stage = 3
        elif stage == 3 and app.dialog:
            assert table.offset == 3 and table.selected == 3
            push([key(9, "\t"), key(13, "\r")])
            stage = 4
        elif stage == 4 and answers:
            assert answers == ["Yes"] and app.focus is table
            push([key(27, "\x1b")])
            stage = 5

    app.on_tick = tick
    app.run()
    assert calls == ["clicked"]
    assert app.mouse_clicks == 2
    assert field.value == "A"
    assert answers == ["Yes"]
    assert (mode(input_handle), mode(output_handle)) == before

    # Exercise the actual event loop's exception path as well as normal exit.
    broken = App(min_width=20, min_height=10)

    def fail(seconds):
        raise ValueError("deliberate callback failure")

    broken.on_tick = fail
    try:
        broken.run()
    except ValueError:
        pass
    else:
        raise AssertionError("Callback exception was swallowed")
    assert (mode(input_handle), mode(output_handle)) == before
    assert not broken.running

    # Supplementary characters must not truncate the following text or ANSI reset.
    terminal = Terminal()
    with terminal:
        terminal.write("\x1b[1;1HA\U0001d400Z\x1b[0mQ")
        # Legacy conhost may substitute the glyph. Verify the trailing ASCII and
        # complete escape sequence independently of font/supplementary support.
        buffer = ct.create_unicode_buffer(3)
        read = wt.DWORD()
        terminal.check(api.ReadConsoleOutputCharacterW(output_handle, buffer, 2,
                                                       Coord(2, 0), ct.byref(read)))
        assert read.value == 2 and buffer.value == "ZQ", ascii(buffer.value)
    print("NATIVE CONSOLE PASS: input, callback, editing, output, normal and exception cleanup")


if __name__ == "__main__":
    main()
