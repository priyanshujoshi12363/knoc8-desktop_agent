import importlib
import subprocess
import sys
import time
from pathlib import Path

from logger import get_logger

log = get_logger("bootstrap")

BASE = Path(__file__).resolve().parent
FLAG = BASE / ".setup_complete"

# import-name -> friendly component name (shown to the user, no internals)
_REQUIRED = [
    ("serial", "device link"),
    ("requests", "network"),
    ("numpy", "audio engine"),
    ("faster_whisper", "speech recognition"),
    ("pyttsx3", "voice"),
    ("pyautogui", "automation"),
    ("pyperclip", "clipboard"),
    ("pygetwindow", "window control"),
    ("plyer", "notifications"),
    ("scipy", "noise filter"),
    ("noisereduce", "noise cancellation"),
]


def _missing() -> list[tuple[str, str]]:
    miss = []
    for mod, name in _REQUIRED:
        try:
            importlib.import_module(mod)
        except Exception:
            miss.append((mod, name))
    return miss


def _install_dependencies() -> bool:
    """Install the Python components from requirements.txt (quietly)."""
    req = BASE / "requirements.txt"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req), "--quiet",
             "--disable-pip-version-check"],
            capture_output=True, text=True, timeout=1800,
        )
        if proc.returncode != 0:
            log.error("Dependency install failed: %s", proc.stderr[-400:])
        return proc.returncode == 0
    except Exception as exc:
        log.error("Dependency install error: %s", exc)
        return False


def _key_field(provider: str) -> str:
    return {
        "ollama": "OLLAMA_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider, "OLLAMA_API_KEY")


def has_api_key() -> bool:
    from settings import load_env

    values = load_env()
    provider = values.get("KNOC8_LLM_PROVIDER", "ollama").lower()
    return bool(values.get(_key_field(provider)))


def needs_setup() -> bool:
    return not FLAG.exists() or not has_api_key()


def run_first_time_setup() -> None:
    import ui

    ui.section("First-time setup")

    # 1) Components / dependencies
    miss = _missing()
    if miss:
        with ui.task("Components") as t:
            t.update(f"downloading {len(miss)} packages, this runs once")
            ok = _install_dependencies()
            still = _missing()
            if not ok or still:
                t.update("some components failed - check your connection")
            else:
                t.update(f"installed {len(miss)} packages")
    else:
        ui.setup_step("Components", "all present")

    # 2) API key via the settings panel
    if not has_api_key():
        ui.setup_step("AI provider", "no API key yet", "warn")
        try:
            import settings_web

            url = settings_web.launch()
            ui.info(f"Opened {url} - choose a provider, paste your key, Save.")
        except Exception as exc:
            log.error("Could not open settings: %s", exc)
            ui.error("Could not open settings. Run:  python settings_web.py")
        with ui.task("Waiting for your API key") as t:
            while not has_api_key():
                time.sleep(2)
            t.update("saved")
    else:
        ui.setup_step("AI provider", "API key present")

    FLAG.touch()
    ui.setup_step("Setup complete", "", "ok")
