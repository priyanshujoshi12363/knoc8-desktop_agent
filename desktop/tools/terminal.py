import os
import re
import subprocess

from logger import get_logger
from tools.base import Action

log = get_logger("terminal")

_cwd = os.path.expanduser("~")

# Known-safe command starts — these run without asking.
_ALLOW_PREFIXES = {
    "npm", "npx", "pnpm", "yarn", "node", "bun", "deno",
    "python", "python3", "py", "pip", "pip3", "uv", "poetry", "pytest",
    "git", "gh", "code", "cursor",
    "mkdir", "cd", "dir", "ls", "echo", "type", "cls", "clear", "pwd",
    "where", "whoami", "hostname", "date", "time", "tree",
    "go", "cargo", "rustc", "dotnet", "java", "javac", "mvn", "gradle",
    "vite", "tsc", "eslint", "prettier", "make", "cmake",
    "ping", "ipconfig", "systeminfo", "tasklist", "ver", "chcp",
}

# Never run these without an explicit, loud confirmation (hard-blocked class).
_HARD_BLOCK = [
    r"\bformat\b", r"\bdiskpart\b", r"\bbcdedit\b", r"\bcipher\s+/w",
    r"\|\s*iex\b", r"\|\s*Invoke-Expression", r"Invoke-WebRequest.*\|\s*iex",
    r"Set-ExecutionPolicy", r"Set-MpPreference", r"Add-MpPreference",
    r"\bvssadmin\b", r"\bwbadmin\b", r"\bfsutil\b", r"\bschtasks\b",
    r"\breg\s+(add|delete)\b", r"\bnet\s+user\b", r"\bnet\s+localgroup\b",
    r"rm\s+-rf\s+[/\\~]", r"\bdel\b.*\/[sq]", r"\brd\b.*\/s", r"rmdir.*\/s",
    r"Remove-Item.*-Recurse", r"\bmkfs\b", r":\s*>\s*", r"\bshutdown\b",
]

# Common but risky — always confirm, allowed once approved.
_CONFIRM_PATTERNS = [
    r"\brm\b", r"\bdel\b", r"\brmdir\b", r"\brd\b", r"Remove-Item",
    r"\bmove\b", r"\bmv\b", r"\btaskkill\b", r"\bkill\b", r"\bcurl\b",
    r"Invoke-WebRequest", r"\bwget\b", r"\bmklink\b", r"\bicacls\b",
    r"\battrib\b", r"\bnetsh\b", r"\bpowercfg\b", r"\bsc\b\s",
]


def classify(command: str) -> str:
    """Return 'block', 'confirm', or 'safe' for a shell command."""
    cmd = command.strip()
    for pat in _HARD_BLOCK:
        if re.search(pat, cmd, re.IGNORECASE):
            return "block"
    for pat in _CONFIRM_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return "confirm"
    # Chained/piped commands: only safe if every segment is safe.
    segments = re.split(r"&&|\|\||\||;|&", cmd)
    for seg in segments:
        token = seg.strip().split()[0].lower() if seg.strip() else ""
        token = token.strip('"')
        if token and token not in _ALLOW_PREFIXES:
            return "confirm"
    return "safe"


def is_dangerous(command: str) -> bool:
    return classify(command) != "safe"


def run(command: str, timeout: int = 120) -> str:
    global _cwd

    if "&&" not in command and "|" not in command:
        cd_match = re.fullmatch(r"\s*cd\s+(?:/d\s+)?(.+?)\s*", command)
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
