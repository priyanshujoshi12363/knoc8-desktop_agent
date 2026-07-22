import pyautogui

from tools.base import Action

pyautogui.FAILSAFE = True


def move(x: int, y: int) -> str:
    pyautogui.moveTo(int(x), int(y), duration=0.2)
    return f"Moved cursor to ({x}, {y})."


def click() -> str:
    pyautogui.click()
    return "Left click done."


def right_click() -> str:
    pyautogui.rightClick()
    return "Right click done."


def double_click() -> str:
    pyautogui.doubleClick()
    return "Double click done."


def scroll(amount: int) -> str:
    pyautogui.scroll(int(amount))
    direction = "up" if int(amount) > 0 else "down"
    return f"Scrolled {direction}."


ACTIONS = {
    "move": Action(move, "Move the mouse cursor to screen coordinates.",
                   {"x": "x coordinate", "y": "y coordinate"}),
    "click": Action(click, "Left click at the current position."),
    "right_click": Action(right_click, "Right click at the current position."),
    "double_click": Action(double_click, "Double click at the current position."),
    "scroll": Action(scroll, "Scroll the wheel.",
                     {"amount": "positive = up, negative = down, e.g. -500"}),
}
