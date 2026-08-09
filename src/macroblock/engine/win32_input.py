"""Thin, physical-pixel-aware Win32 SendInput wrapper."""

from __future__ import annotations

import ctypes
import logging
import math
import sys
import threading
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
WHEEL_DELTA = 120
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class INPUTUNION(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = (("type", wintypes.DWORD), ("union", INPUTUNION))


NAMED_KEYS = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "CAPSLOCK": 0x14,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "ALT": 0x12,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "PRINTSCREEN": 0x2C,
    "WIN": 0x5B,
    "WINDOWS": 0x5B,
    "MENU": 0x5D,
    "NUMLOCK": 0x90,
    "SCROLLLOCK": 0x91,
    "PAUSE": 0x13,
    "SEMICOLON": 0xBA,
    "PLUS": 0xBB,
    "COMMA": 0xBC,
    "MINUS": 0xBD,
    "PERIOD": 0xBE,
    "SLASH": 0xBF,
    "BACKTICK": 0xC0,
    "LEFTBRACKET": 0xDB,
    "BACKSLASH": 0xDC,
    "RIGHTBRACKET": 0xDD,
    "QUOTE": 0xDE,
}

MOUSE_BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, 0),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, 0),
    "back": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
    "forward": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
}


class InputSimulationError(OSError):
    pass


class InputController:
    """Simulates mouse and keyboard input without Qt focus assumptions."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Input simulation is only available on Windows.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        )
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
        self.user32.VkKeyScanW.restype = wintypes.SHORT
        self.user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetAsyncKeyState.restype = wintypes.SHORT
        self.user32.MonitorFromPoint.argtypes = (wintypes.POINT, wintypes.DWORD)
        self.user32.MonitorFromPoint.restype = wintypes.HMONITOR

    def _send(self, *inputs: INPUT) -> None:
        buffer = (INPUT * len(inputs))(*inputs)
        sent = self.user32.SendInput(len(buffer), buffer, ctypes.sizeof(INPUT))
        if sent != len(buffer):
            error = ctypes.get_last_error()
            raise InputSimulationError(error, "SendInput did not send every event")

    @staticmethod
    def _mouse_input(flags: int, *, dx: int = 0, dy: int = 0, data: int = 0) -> INPUT:
        return INPUT(
            type=INPUT_MOUSE,
            union=INPUTUNION(
                mi=MOUSEINPUT(
                    dx,
                    dy,
                    ctypes.c_ulong(data).value,
                    flags,
                    0,
                    0,
                )
            ),
        )

    @staticmethod
    def _key_input(vk: int, *, scan: int = 0, flags: int = 0) -> INPUT:
        return INPUT(
            type=INPUT_KEYBOARD,
            union=INPUTUNION(ki=KEYBDINPUT(vk, scan, flags, 0, 0)),
        )

    def virtual_screen_bounds(self) -> tuple[int, int, int, int]:
        return tuple(
            self.user32.GetSystemMetrics(metric)
            for metric in (
                SM_XVIRTUALSCREEN,
                SM_YVIRTUALSCREEN,
                SM_CXVIRTUALSCREEN,
                SM_CYVIRTUALSCREEN,
            )
        )

    def coordinate_is_visible(self, x: int, y: int) -> bool:
        return bool(self.user32.MonitorFromPoint(wintypes.POINT(x, y), 0))

    def _normalized_position(self, x: int, y: int) -> tuple[int, int] | None:
        if not self.coordinate_is_visible(x, y):
            logger.warning(
                "Skipping coordinate (%s, %s): it is outside every connected monitor.",
                x,
                y,
            )
            return None
        left, top, width, height = self.virtual_screen_bounds()
        normalized_x = round((x - left) * 65535 / max(1, width - 1))
        normalized_y = round((y - top) * 65535 / max(1, height - 1))
        return normalized_x, normalized_y

    def move_to(
        self,
        x: int,
        y: int,
        duration: float = 0.0,
        abort_event: threading.Event | None = None,
    ) -> bool:
        target = self._normalized_position(x, y)
        if target is None:
            return False
        duration = float(duration)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("Mouse move duration must be a finite non-negative number.")
        if duration == 0:
            self._send(
                self._mouse_input(
                    MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                    dx=target[0],
                    dy=target[1],
                )
            )
            return True

        start = self._normalized_position(*self.cursor_position())
        if start is None:
            start = target
        steps = max(2, min(240, round(duration * 60)))
        started = time.monotonic()
        for step in range(1, steps + 1):
            deadline = started + duration * step / steps
            remaining = deadline - time.monotonic()
            if remaining > 0:
                if abort_event is not None:
                    if abort_event.wait(remaining):
                        return False
                else:
                    time.sleep(remaining)
            progress = step / steps
            self._send(
                self._mouse_input(
                    MOUSEEVENTF_MOVE
                    | MOUSEEVENTF_ABSOLUTE
                    | MOUSEEVENTF_VIRTUALDESK,
                    dx=round(start[0] + (target[0] - start[0]) * progress),
                    dy=round(start[1] + (target[1] - start[1]) * progress),
                )
            )
        return True

    @staticmethod
    def _mouse_button_flags(button: str) -> tuple[int, int, int]:
        try:
            return MOUSE_BUTTON_FLAGS[button]
        except KeyError as error:
            choices = ", ".join(MOUSE_BUTTON_FLAGS)
            raise ValueError(
                f"Unknown mouse button '{button}'. Choose one of: {choices}."
            ) from error

    def click(self, button: str = "left", count: int = 1) -> None:
        down, up, data = self._mouse_button_flags(button)
        for _ in range(count):
            self._send(
                self._mouse_input(down, data=data),
                self._mouse_input(up, data=data),
            )

    def button_down(self, button: str = "left") -> None:
        down, _up, data = self._mouse_button_flags(button)
        self._send(self._mouse_input(down, data=data))

    def button_up(self, button: str = "left") -> None:
        _down, up, data = self._mouse_button_flags(button)
        self._send(self._mouse_input(up, data=data))

    def move_by(
        self,
        dx: int,
        dy: int,
        duration: float = 0.0,
        abort_event: threading.Event | None = None,
    ) -> bool:
        x, y = self.cursor_position()
        return self.move_to(x + dx, y + dy, duration, abort_event)

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        start = self._normalized_position(x1, y1)
        end = self._normalized_position(x2, y2)
        if start is None or end is None:
            return False
        self._send(
            self._mouse_input(
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                dx=start[0],
                dy=start[1],
            ),
            self._mouse_input(MOUSEEVENTF_LEFTDOWN),
            self._mouse_input(
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                dx=end[0],
                dy=end[1],
            ),
            self._mouse_input(MOUSEEVENTF_LEFTUP),
        )
        return True

    def scroll(self, amount: int) -> None:
        self._send(self._mouse_input(MOUSEEVENTF_WHEEL, data=amount * WHEEL_DELTA))

    def resolve_key(self, key: str) -> int:
        normalized = (
            key.strip().upper().replace(" ", "").replace("_", "").replace("-", "")
        )
        if normalized.startswith("ARROW"):
            normalized = normalized[5:]
        if normalized in NAMED_KEYS:
            return NAMED_KEYS[normalized]
        if normalized.startswith("F") and normalized[1:].isdigit():
            number = int(normalized[1:])
            if 1 <= number <= 24:
                return 0x6F + number
        if len(normalized) == 1 and (
            "A" <= normalized <= "Z" or "0" <= normalized <= "9"
        ):
            return ord(normalized)
        if len(normalized) == 1:
            value = self.user32.VkKeyScanW(normalized)
            if value != -1:
                return value & 0xFF
        raise ValueError(f"Unknown key '{key}'.")

    def hotkey_is_down(self, hotkey: str) -> bool:
        keys = [part.strip() for part in hotkey.split("+") if part.strip()]
        if not keys:
            raise ValueError("Hotkey must contain at least one key.")
        return all(
            bool(self.user32.GetAsyncKeyState(self.resolve_key(key)) & 0x8000)
            for key in keys
        )

    def key_down(self, key: str) -> None:
        self._send(self._key_input(self.resolve_key(key)))

    def key_up(self, key: str) -> None:
        self._send(self._key_input(self.resolve_key(key), flags=KEYEVENTF_KEYUP))

    def press_key(self, key: str) -> None:
        vk = self.resolve_key(key)
        self._send(self._key_input(vk), self._key_input(vk, flags=KEYEVENTF_KEYUP))

    def key_combo(self, keys: list[str]) -> None:
        resolved = [self.resolve_key(key) for key in keys]
        self._send(
            *(self._key_input(vk) for vk in resolved),
            *(self._key_input(vk, flags=KEYEVENTF_KEYUP) for vk in reversed(resolved)),
        )

    def type_text(self, text: str) -> None:
        inputs: list[INPUT] = []
        encoded = text.encode("utf-16-le")
        for offset in range(0, len(encoded), 2):
            code_unit = int.from_bytes(encoded[offset : offset + 2], "little")
            inputs.extend(
                (
                    self._key_input(0, scan=code_unit, flags=KEYEVENTF_UNICODE),
                    self._key_input(
                        0,
                        scan=code_unit,
                        flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                    ),
                )
            )
        if inputs:
            self._send(*inputs)

    def cursor_position(self) -> tuple[int, int]:
        point = wintypes.POINT()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise ctypes.WinError(ctypes.get_last_error())
        return point.x, point.y
