"""Windows console plumbing, isolated from the ordinary Python widget code.

No DLL is shipped: ctypes calls kernel32, which is part of Windows itself.
Windows sends structured mouse/key records; ANSI sequences draw the screen.
"""

import ctypes as ct
from ctypes import wintypes as wt
from dataclasses import dataclass
import os


@dataclass
class Event:
    kind: str
    key: str = ""
    text: str = ""
    x: int = 0
    y: int = 0
    shift: bool = False
    delta: int = 0  # Scroll notches; positive is down.
    clicks: int = 1


# These structures mirror Microsoft's console API definitions.
class Coord(ct.Structure):
    _fields_ = [("x", wt.SHORT), ("y", wt.SHORT)]


class Rect(ct.Structure):
    _fields_ = [(name, wt.SHORT) for name in ("left", "top", "right", "bottom")]


class ScreenInfo(ct.Structure):
    _fields_ = [("size", Coord), ("cursor", Coord), ("attributes", wt.WORD),
                ("window", Rect), ("maximum_size", Coord)]


class KeyRecord(ct.Structure):
    _fields_ = [("down", wt.BOOL), ("repeat", wt.WORD), ("code", wt.WORD),
                ("scan", wt.WORD), ("char", wt.WCHAR), ("modifiers", wt.DWORD)]


class MouseRecord(ct.Structure):
    _fields_ = [("position", Coord), ("buttons", wt.DWORD),
                ("modifiers", wt.DWORD), ("flags", wt.DWORD)]


class RecordData(ct.Union):
    _fields_ = [("key", KeyRecord), ("mouse", MouseRecord),
                ("size", Coord), ("focused", wt.BOOL)]


class InputRecord(ct.Structure):
    _fields_ = [("kind", wt.WORD), ("data", RecordData)]


class Decoder:
    """Convert OS records to a few simple events; no widgets know about Win32."""

    KEYS = {8: "backspace", 9: "tab", 13: "enter", 27: "escape", 32: "space",
            33: "pageup", 34: "pagedown", 35: "end", 36: "home", 37: "left", 38: "up", 39: "right",
            40: "down", 46: "delete"}

    def __init__(self):
        self.left_down = False
        self.wheel_delta = 0

    def decode(self, record, origin=(0, 0)):
        if record.kind == 1:  # KEY_EVENT
            key = record.data.key
            if key.down:
                name = self.KEYS.get(key.code, "")
                if key.code == 67 and key.modifiers & 0x000C:  # Ctrl+C
                    name = "quit"
                event = Event("key", key=name, text=key.char,
                              shift=bool(key.modifiers & 0x0010))
                return [event] * max(1, key.repeat)
        elif record.kind == 2:  # MOUSE_EVENT
            mouse = record.data.mouse
            if mouse.flags & 4:  # Signed high word; accumulate precision-wheel deltas.
                self.wheel_delta += ct.c_short(mouse.buttons >> 16).value
                steps = int(self.wheel_delta / 120)
                self.wheel_delta -= steps * 120
                return ([Event("scroll", x=mouse.position.x - origin[0],
                               y=mouse.position.y - origin[1], delta=-steps)] if steps else [])
            if mouse.flags & 8:  # Horizontal scrolling is not implemented.
                return []
            down = bool(mouse.buttons & 1)
            kind = "move"
            if down != self.left_down:
                kind = "down" if down else "up"
            self.left_down = down
            return [Event(kind, x=mouse.position.x - origin[0],
                          y=mouse.position.y - origin[1], clicks=2 if mouse.flags & 2 else 1)]
        elif record.kind == 4:  # WINDOW_BUFFER_SIZE_EVENT
            return [Event("resize")]
        elif record.kind == 16 and not record.data.focused:  # FOCUS_EVENT
            self.left_down = False
            return [Event("blur")]
        return []


class Terminal:
    """Context manager: restore console modes and the old screen even on errors."""

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("CellKit currently supports Windows only.")
        self.api = ct.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "GetStdHandle": ([wt.DWORD], wt.HANDLE),
            "GetConsoleMode": ([wt.HANDLE, ct.POINTER(wt.DWORD)], wt.BOOL),
            "SetConsoleMode": ([wt.HANDLE, wt.DWORD], wt.BOOL),
            "GetConsoleScreenBufferInfo": ([wt.HANDLE, ct.POINTER(ScreenInfo)], wt.BOOL),
            "ReadConsoleInputW": ([wt.HANDLE, ct.POINTER(InputRecord), wt.DWORD,
                                   ct.POINTER(wt.DWORD)], wt.BOOL),
            "WriteConsoleW": ([wt.HANDLE, wt.LPCWSTR, wt.DWORD,
                               ct.POINTER(wt.DWORD), wt.LPVOID], wt.BOOL),
            "WaitForSingleObject": ([wt.HANDLE, wt.DWORD], wt.DWORD),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.input = self.api.GetStdHandle(-10)
        self.output = self.api.GetStdHandle(-11)
        self.old_input, self.old_output = wt.DWORD(), wt.DWORD()
        self.decoder = Decoder()

    @staticmethod
    def check(result):
        if not result:
            raise ct.WinError(ct.get_last_error())

    def __enter__(self):
        if not (self.api.GetConsoleMode(self.input, ct.byref(self.old_input)) and
                self.api.GetConsoleMode(self.output, ct.byref(self.old_output))):
            raise RuntimeError("Run in an interactive Windows terminal, not an Output "
                               "pane, PowerShell ISE, or a redirected pipe.")
        try:
            # Enable mouse, resize and extended flags. Disable quick-edit selection,
            # line buffering, echo, processed Ctrl+C, and VT input translation.
            mode = (self.old_input.value | 0x0010 | 0x0008 | 0x0080)
            mode &= ~(0x0040 | 0x0002 | 0x0004 | 0x0001 | 0x0200)
            self.check(self.api.SetConsoleMode(self.input, mode))
            self.check(self.api.SetConsoleMode(self.output, self.old_output.value | 0x0005))
            self.write("\x1b[?1049h\x1b[?25l\x1b[0m")  # alternate screen, hide cursor
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_):
        try:
            self.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        finally:
            self.api.SetConsoleMode(self.input, self.old_input.value)
            self.api.SetConsoleMode(self.output, self.old_output.value)

    def info(self):
        info = ScreenInfo()
        self.check(self.api.GetConsoleScreenBufferInfo(self.output, ct.byref(info)))
        return info

    def size(self):
        window = self.info().window
        # Reserve the last column to avoid automatic wrap/scroll at bottom right.
        return max(1, window.right - window.left), max(1, window.bottom - window.top + 1)

    def write(self, text):
        # Win32 counts UTF-16 units, not Python code points. Keep the buffer alive
        # across partial writes, advancing by units even within a surrogate pair.
        if text:
            data = text.encode("utf-16-le")
            buffer = ct.create_string_buffer(data)
            total, offset = len(data) // 2, 0
            while offset < total:
                written = wt.DWORD()
                pointer = ct.cast(ct.byref(buffer, offset * 2), wt.LPCWSTR)
                self.check(self.api.WriteConsoleW(self.output, pointer, total - offset,
                                                 ct.byref(written), None))
                if not 0 < written.value <= total - offset:
                    raise OSError("WriteConsoleW returned an invalid write count")
                offset += written.value

    def read(self, timeout_ms=30):
        result = self.api.WaitForSingleObject(self.input, timeout_ms)
        if result == 258:  # WAIT_TIMEOUT
            return []
        if result != 0:
            raise ct.WinError(ct.get_last_error())
        records = (InputRecord * 128)()
        count = wt.DWORD()
        self.check(self.api.ReadConsoleInputW(self.input, records, len(records), ct.byref(count)))
        window = self.info().window
        events = []
        for record in records[:count.value]:
            events.extend(self.decoder.decode(record, (window.left, window.top)))
        return events
