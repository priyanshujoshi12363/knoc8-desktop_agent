import subprocess

from logger import get_logger
from tools.base import Action

log = get_logger("apps")

_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cursor": "cursor",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "terminal": "wt",
    "windows terminal": "wt",
    "wt": "wt",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "spotify": "spotify",
    "settings": "ms-settings:",
}

_PROCESSES = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "cursor": "Cursor.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "spotify": "Spotify.exe",
    "paint": "mspaint.exe",
}


def open_app(name: str) -> str:
    target = _ALIASES.get(name.lower().strip(), name)
    log.info("Opening application: %s (%s)", name, target)
    result = subprocess.run(
        f'start "" "{target}"', shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        return f"Could not open {name}: {result.stderr.strip()}"
    return f"{name} has been opened."


def close_app(name: str) -> str:
    proc = _PROCESSES.get(name.lower().strip(), f"{name}.exe")
    log.info("Closing application: %s (%s)", name, proc)
    result = subprocess.run(
        ["taskkill", "/IM", proc, "/T"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return f"Could not close {name}: {result.stderr.strip() or 'not running'}"
    return f"{name} has been closed."


def focus_app(name: str) -> str:
    import pygetwindow as gw

    matches = [w for w in gw.getAllWindows() if name.lower() in w.title.lower()]
    if not matches:
        return f"No window found matching '{name}'."
    win = matches[0]
    if win.isMinimized:
        win.restore()
    win.activate()
    return f"Focused window: {win.title}"


ACTIONS = {
    "open": Action(open_app, "Open an application.",
                   {"name": "app name, e.g. 'chrome', 'cursor', 'notepad'"}),
    "close": Action(close_app, "Close an application.",
                    {"name": "app name"}),
    "focus": Action(focus_app, "Bring an application window to the front.",
                    {"name": "part of the window title"}),
}
