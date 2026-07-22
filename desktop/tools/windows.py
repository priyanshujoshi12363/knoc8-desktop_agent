import pygetwindow as gw

from tools.base import Action


def _find(title: str):
    matches = [w for w in gw.getAllWindows()
               if title.lower() in w.title.lower() and w.title.strip()]
    return matches[0] if matches else None


def list_windows() -> str:
    titles = [w.title for w in gw.getAllWindows() if w.title.strip()][:30]
    return "Open windows:\n" + "\n".join(f"- {t}" for t in titles)


def switch(title: str) -> str:
    win = _find(title)
    if not win:
        return f"No window matching '{title}'."
    if win.isMinimized:
        win.restore()
    win.activate()
    return f"Switched to: {win.title}"


def maximize(title: str) -> str:
    win = _find(title)
    if not win:
        return f"No window matching '{title}'."
    win.maximize()
    return f"Maximized: {win.title}"


def minimize(title: str) -> str:
    win = _find(title)
    if not win:
        return f"No window matching '{title}'."
    win.minimize()
    return f"Minimized: {win.title}"


ACTIONS = {
    "list": Action(list_windows, "List the titles of all open windows."),
    "switch": Action(switch, "Switch focus to a window.",
                     {"title": "part of the window title"}),
    "maximize": Action(maximize, "Maximize a window.",
                       {"title": "part of the window title"}),
    "minimize": Action(minimize, "Minimize a window.",
                       {"title": "part of the window title"}),
}
