import ctypes as ct
from ctypes import wintypes as wt
import os
from types import SimpleNamespace
import unittest

from cellkit.terminal import Terminal


@unittest.skipUnless(os.name == "nt", "Windows UTF-16 console API")
class TerminalWriteTests(unittest.TestCase):
    def terminal(self, counts):
        terminal = object.__new__(Terminal)
        terminal.output = 1
        self.output = bytearray()
        self.requests = []
        counts = iter(counts)

        def write(handle, pointer, remaining, written, reserved):
            self.requests.append(remaining)
            count = next(counts, remaining)
            ct.cast(written, ct.POINTER(wt.DWORD))[0] = count
            if 0 < count <= remaining:
                self.output.extend(ct.string_at(pointer, count * 2))
            return True

        terminal.api = SimpleNamespace(WriteConsoleW=write)
        return terminal

    def test_supplementary_character_and_trailing_reset_are_written_in_full(self):
        terminal = self.terminal([])
        text = "A\U0001d400Z\x1b[0m"
        terminal.write(text)
        self.assertEqual(self.output.decode("utf-16-le"), text)

    def test_partial_writes_resume_at_utf16_unit_offset(self):
        terminal = self.terminal([2, 1, 1])
        text = "A\U0001d400Z\x1b[0m"
        terminal.write(text)
        self.assertEqual(self.output.decode("utf-16-le"), text)
        self.assertEqual(self.requests, [8, 6, 5, 4])

    def test_invalid_write_count_fails_without_looping(self):
        for count in (0, 100):
            with self.subTest(count=count):
                terminal = self.terminal([count])
                with self.assertRaises(OSError):
                    terminal.write("text")
                self.assertEqual(len(self.requests), 1)

    def test_empty_output_skips_console_call(self):
        terminal = self.terminal([])
        terminal.write("")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
