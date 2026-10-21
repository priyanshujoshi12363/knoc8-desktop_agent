"""Coding tool — hands real software work to a dedicated coding agent.

Knoc8's planner is one-shot: it writes a plan before anything runs, so it
cannot read a build error and fix it.  Rather than fake that, this tool
delegates to a coding CLI (Claude Code, Cursor, aider, ...) which *does*
loop, and runs it in a visible terminal window inside the target project.
"""

import os
import shutil
import subprocess

import config
from logger import get_logger
from tools.base import Action

log = get_logger("coding")

# name -> (executable, argv template).  "{task}" is replaced with the request.
_AGENTS: dict[str, tuple[str, list[str]]] = {
    "claude": ("claude", ["{task}"]),
    "cursor-agent": ("cursor-agent", ["{task}"]),
    "aider": ("aider", ["--message", "{task}"]),
    "codex": ("codex", ["{task}"]),
    "gemini": ("gemini", ["{task}"]),
}

_EDITORS = ("cursor", "code")

# Never let an autonomous agent loose on these.
_FORBIDDEN_NAMES = {"windows", "system32", "program files", "program files (x86)",
                    "programdata", "appdata", "system volume information"}


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def _guard(path: str) -> str:
    """Return an error string if this directory is unsafe to work in."""
    path = _expand(path)
    drive, tail = os.path.splitdrive(path)
    if tail in ("", "\\", "/"):
        return f"Refusing to work directly in the drive root {path}. Pick a subfolder."
    if os.path.normpath(path) == os.path.normpath(os.path.expanduser("~")):
        return "Refusing to work in your home folder directly. Pick a project folder."
    parts = {p.lower() for p in path.split(os.sep) if p}
    hit = parts & _FORBIDDEN_NAMES
    if hit:
        return f"Refusing to work in a system folder ({', '.join(sorted(hit))})."
    return ""


def available_agents() -> list[str]:
    return [name for name, (exe, _) in _AGENTS.items() if shutil.which(exe)]


def _pick_agent() -> tuple[str, str, list[str]] | None:
    """(name, executable, argv template) for the configured or first found agent."""
    preferred = config.CODING_AGENT.strip().lower()
    order = ([preferred] if preferred in _AGENTS else []) + list(_AGENTS)
    for name in order:
        exe, argv = _AGENTS[name]
        resolved = shutil.which(exe)
        if resolved:
            return name, resolved, argv
    return None


def _launch(task: str, directory: str) -> str:
    agent = _pick_agent()
    if agent is None:
        return ("No coding agent is installed. Install one of: "
                + ", ".join(_AGENTS) + " (Claude Code is recommended).")
    name, exe, template = agent
    argv = [exe] + [part.replace("{task}", task) for part in template]

    log.info("Launching %s in %s: %s", name, directory, task[:120])
    try:

        subprocess.Popen(
            ["cmd", "/k"] + argv,
            cwd=directory,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError as exc:
        log.error("Could not start %s: %s", name, exc)
        return f"Could not start {name}: {exc}"
    return (f"{name} is now building this in a terminal window at {directory}: "
            f"{task[:160]}")


def build(task: str, directory: str) -> str:
    """Create the project folder if needed and start a coding agent in it."""
    problem = _guard(directory)
    if problem:
        return problem
    directory = _expand(directory)
    existed = os.path.isdir(directory)
    os.makedirs(directory, exist_ok=True)
    note = "" if existed else "Created the project folder. "
    return note + _launch(task, directory)


def continue_task(task: str, directory: str) -> str:
    """Continue work inside an existing project."""
    problem = _guard(directory)
    if problem:
        return problem
    directory = _expand(directory)
    if not os.path.isdir(directory):
        return f"No such project folder: {directory}. Use coding.build to start one."
    return _launch(task, directory)


def open_project(directory: str) -> str:
    """Open a project folder in the user's editor."""
    problem = _guard(directory)
    if problem:
        return problem
    directory = _expand(directory)
    if not os.path.isdir(directory):
        return f"No such folder: {directory}"
    for editor in _EDITORS:
        exe = shutil.which(editor)
        if exe:
            subprocess.Popen([exe, directory], shell=False)
            return f"Opened {directory} in {editor}."
    subprocess.run(["explorer", directory])
    return f"Opened {directory} in File Explorer."


def list_agents() -> str:
    found = available_agents()
    if not found:
        return ("No coding agent found. Install Claude Code to let Knoc8 build "
                "full projects.")
    return "Available coding agents: " + ", ".join(found) + (
        f" (using: {_pick_agent()[0]})")


ACTIONS = {
    "build": Action(
        build,
        "Build a NEW software project. Creates the folder and hands the whole "
        "job to a real coding agent that writes files, installs packages, runs "
        "the build and fixes its own errors. Use this for any real programming "
        "request instead of writing source files yourself.",
        {"task": "full description of what to build, in one sentence",
         "directory": "project folder path, e.g. D:\\projects\\todo-app"},
        dangerous=True,
    ),
    "continue_task": Action(
        continue_task,
        "Continue or modify an EXISTING project with the coding agent "
        "(add a feature, fix a bug, refactor).",
        {"task": "what to change", "directory": "the existing project folder"},
        dangerous=True,
    ),
    "open_project": Action(
        open_project,
        "Open a project folder in the code editor (Cursor or VS Code).",
        {"directory": "the project folder"},
    ),
    "list_agents": Action(
        list_agents, "Check which coding agents are installed on this PC."),
}
