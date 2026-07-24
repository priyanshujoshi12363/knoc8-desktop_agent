from tools import (
    applications,
    browser,
    clipboard,
    filesystem,
    keyboard,
    mouse,
    notification,
    settings_tool,
    system,
    terminal,
    wait,
    windows,
)
from tools.base import Action

REGISTRY: dict[str, dict[str, Action]] = {
    "terminal": terminal.ACTIONS,
    "application": applications.ACTIONS,
    "browser": browser.ACTIONS,
    "keyboard": keyboard.ACTIONS,
    "mouse": mouse.ACTIONS,
    "clipboard": clipboard.ACTIONS,
    "filesystem": filesystem.ACTIONS,
    "windows": windows.ACTIONS,
    "notification": notification.ACTIONS,
    "system": system.ACTIONS,
    "wait": wait.ACTIONS,
    "settings": settings_tool.ACTIONS,
}


def get_action(tool: str, action: str) -> Action | None:
    return REGISTRY.get(tool, {}).get(action)


def describe_tools() -> str:
    lines: list[str] = []
    for tool_name, actions in REGISTRY.items():
        lines.append(f"## {tool_name}")
        for action_name, action in actions.items():
            params = ", ".join(f'{k}: {v}' for k, v in action.params.items())
            flag = " [REQUIRES USER CONFIRMATION]" if action.dangerous else ""
            lines.append(f"- {action_name}({params}) - {action.desc}{flag}")
    return "\n".join(lines)
