import os
import re
import subprocess

from logger import get_logger
from tools.base import Action

log = get_logger("terminal")

_cwd = os.path.expanduser("~")

_DANGEROUS_PATTERNS = [
    r"\brm\b", r"\bdel\b", r"\brmdir\b", r"\bformat\b", r"\bshutdown\b",
    r"\brestart\b", r"\bdiskpart\b", r"\breg\s+(add|delete)\b", r"\bmklink\b",
    r"Remove-Item", r"\btaskkill\b.*\/f", r"\bnet\s+user\b", r"\bcipher\b",
]


def is_dangerous(command: str) -> bool:
    return any(re.search(p, command, re.IGNORECASE) for p in _DANGEROUS_PATTERNS)


def run(command: str, timeout: int = 120) -> str:
    global _cwd

    cd_match = re.fullmatch(r"\s*cd\s+(.+?)\s*", command)
    if cd_match:
        target = os.path.expanduser(cd_match.group(1).strip('"'))
        new_dir = os.path.abspath(os.path.join(_cwd, target))
        if os.path.isdir(new_dir):
            _cwd = new_dir
            return f"Working directory is now {_cwd}"
        return f"Directory not found: {new_dir}"

    log.info("RUN [%s]> %s", _cwd, command)
    try:
        proc = subprocess.run(
            command, shell=True, cwd=_cwd, capture_output=True,
            text=True, timeout=timeout, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s: {command}"

    output = (proc.stdout or "") + (proc.stderr or "")
    output = output.strip() or "(no output)"
    if len(output) > 4000:
        output = output[:2000] + "\n...(truncated)...\n" + output[-1500:]
    status = "SUCCESS" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
    log.info("Result: %s", status)
    return f"{status}\n{output}"


def run_background(command: str) -> str:
    log.info("RUN-BG [%s]> %s", _cwd, command)
    subprocess.Popen(
        f'start "Knoc8" cmd /k "{command}"', shell=True, cwd=_cwd
    )
    return f"Started in a new terminal window: {command}"


def current_dir() -> str:
    return f"Current working directory: {_cwd}"


ACTIONS = {
    "run": Action(
        run,
        "Run a shell command and capture its output (npm, git, pip, mkdir, dir...). "
        "Use 'cd <path>' to change directory.",
        {"command": "the exact shell command to execute"},
    ),
    "run_background": Action(
        run_background,
        "Run a long-lived command (dev server, watcher) in a new terminal window.",
        {"command": "the shell command, e.g. 'npm run dev'"},
    ),
    "current_dir": Action(current_dir, "Get the current working directory."),
}
