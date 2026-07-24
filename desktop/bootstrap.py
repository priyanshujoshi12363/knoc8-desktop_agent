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
    bar = "=" * 54
    print(f"\n{bar}\n   Welcome to Knoc8  —  first-time setup\n{bar}\n")

    # 1) Components / dependencies
    print("  Checking components...")
    miss = _missing()
    if miss:
        print(f"  Downloading {len(miss)} components. This runs once and may")
        print("  take a few minutes — please keep the device connected.\n")
        if _install_dependencies():
            still = _missing()
            if still:
                print("  Some components could not be installed:",
                      ", ".join(n for _, n in still))
                print("  Please check your internet connection and restart.\n")
            else:
                print("  All components installed successfully.\n")
        else:
            print("  Download failed — check your internet connection and restart.\n")
    else:
        print("  All components ready.\n")

    # 2) API key via the settings panel
    if not has_api_key():
        print("  Opening the Knoc8 settings page in your browser.")
        print("  Choose your AI provider, paste your API key, and click Save.")
        print("  (Each key field has a 'Get your key' link if you need one.)\n")
        try:
            import settings_web
            settings_web.launch()
        except Exception as exc:
            log.error("Could not open settings: %s", exc)
            print("  Could not open settings automatically. Run:  python settings_web.py")
        print("  Waiting for you to save your API key...")
        while not has_api_key():
            time.sleep(2)
        print("  API key saved.\n")

    FLAG.touch()
    print(f"{bar}\n   Setup complete!  Say 'Hey Agent' to begin.\n{bar}\n")
