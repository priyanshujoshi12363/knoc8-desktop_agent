import pyautogui

from logger import get_logger
from tools.base import Action

log = get_logger("keyboard")

pyautogui.FAILSAFE = True


def type_text(text: str) -> str:
    log.info("Typing %d characters", len(text))
    pyautogui.write(text, interval=0.02)
    return f"Typed: {text[:80]}"


def press(key: str) -> str:
    pyautogui.press(key.lower())
    return f"Pressed {key}."


def hotkey(keys: str) -> str:
    parts = [k.strip().lower() for k in keys.split("+")]
    pyautogui.hotkey(*parts)
    return f"Pressed shortcut {keys}."


ACTIONS = {
    "type": Action(type_text, "Type text at the current cursor position.",
                   {"text": "the text to type"}),
    "press": Action(press, "Press a single key.",
                    {"key": "key name: enter, esc, tab, up, down, f5..."}),
    "hotkey": Action(hotkey, "Press a keyboard shortcut.",
                     {"keys": "keys joined with '+', e.g. 'ctrl+s'"}),
}
