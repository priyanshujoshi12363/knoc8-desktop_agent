import pyautogui
import pyperclip

from tools.base import Action


def copy_text(text: str) -> str:
    pyperclip.copy(text)
    return "Text copied to clipboard."


def copy_selection() -> str:
    pyautogui.hotkey("ctrl", "c")
    return "Sent Ctrl+C to copy the current selection."


def paste() -> str:
    pyautogui.hotkey("ctrl", "v")
    return "Pasted clipboard content."


def read() -> str:
    content = pyperclip.paste()
    if not content:
        return "Clipboard is empty."
    return f"Clipboard content: {content[:1000]}"


ACTIONS = {
    "copy_text": Action(copy_text, "Put specific text on the clipboard.",
                        {"text": "the text to copy"}),
    "copy_selection": Action(copy_selection, "Copy the current selection (Ctrl+C)."),
    "paste": Action(paste, "Paste the clipboard (Ctrl+V)."),
    "read": Action(read, "Read the current clipboard content."),
}
