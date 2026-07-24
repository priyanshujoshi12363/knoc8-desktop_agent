import sys
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"

SCHEMA = [
    ("KNOC8_LLM_PROVIDER", "LLM provider (ollama / anthropic / openai)", "ollama"),
    ("OLLAMA_API_KEY", "Ollama Cloud API key", ""),
    ("KNOC8_LLM_MODEL", "Ollama model", "minimax-m3"),
    ("ANTHROPIC_API_KEY", "Anthropic (Claude) API key", ""),
    ("KNOC8_ANTHROPIC_MODEL", "Claude model", "claude-opus-4-8"),
    ("OPENAI_API_KEY", "OpenAI API key", ""),
    ("KNOC8_OPENAI_MODEL", "OpenAI model", "gpt-4o"),
    ("KNOC8_SERIAL_PORT", "ESP32 COM port", "COM17"),
    ("KNOC8_SERIAL_BAUD", "Serial baud rate", "921600"),
    ("KNOC8_WAKE_WORD", "Wake word phrase", "hey agent"),
    ("KNOC8_WAKE_MODEL", "Whisper model for wake word (tiny/base)", "tiny"),
    ("KNOC8_WHISPER_MODEL", "Whisper model for commands (tiny/base/small)", "base"),
    ("KNOC8_MIC_THRESHOLD", "Mic energy threshold for speech (lower = more sensitive)", "300"),
    ("KNOC8_SILENCE_MS", "Silence ms that ends a command", "1200"),
    ("KNOC8_TTS_RATE", "Voice speed (words per minute)", "175"),
    ("KNOC8_CHROME_PROFILE", "Default Chrome profile (empty = ask by voice)", ""),
    ("KNOC8_NOISE_REDUCTION", "Noise cancellation (1 = on, 0 = off)", "1"),
]


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def save_env(values: dict[str, str]) -> None:
    lines = ["# Knoc8 Desktop Agent settings (edit with: python settings.py)"]
    known = {key for key, _, _ in SCHEMA}
    for key, _, _ in SCHEMA:
        if key in values and values[key] != "":
            lines.append(f"{key}={values[key]}")
    for key, val in values.items():
        if key not in known:
            lines.append(f"{key}={val}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mask(key: str, val: str) -> str:
    if "KEY" in key and len(val) > 8:
        return val[:4] + "..." + val[-4:]
    return val or "(not set)"


def show(values: dict[str, str]) -> None:
    print()
    print("  Knoc8 Settings")
    print("  " + "-" * 60)
    for i, (key, desc, default) in enumerate(SCHEMA, 1):
        current = values.get(key, "")
        shown = mask(key, current) if current else f"(default: {default})" if default else "(not set)"
        print(f"  {i:2}. {desc}")
        print(f"      {key} = {shown}")
    print()


def interactive() -> None:
    values = load_env()
    while True:
        show(values)
        choice = input("  Enter number to change (or q to quit): ").strip().lower()
        if choice in {"q", "quit", "exit", ""}:
            break
        if not choice.isdigit() or not 1 <= int(choice) <= len(SCHEMA):
            print("  Invalid choice.")
            continue
        key, desc, default = SCHEMA[int(choice) - 1]
        current = values.get(key, default)
        print(f"\n  {desc}")
        print(f"  Current: {mask(key, current) if current else '(not set)'}")
        if key == "KNOC8_CHROME_PROFILE":
            try:
                sys.path.insert(0, str(ENV_FILE.parent))
                from tools.browser import chrome_profiles

                names = list(chrome_profiles().values())
                if names:
                    print("  Available profiles:", ", ".join(names))
            except Exception:
                pass
        new = input("  New value (blank = keep, '-' = clear): ").strip()
        if new == "-":
            values.pop(key, None)
            save_env(values)
            print(f"  {key} cleared.")
        elif new:
            values[key] = new
            save_env(values)
            print(f"  {key} set to {mask(key, new)}.")
    print("\n  Saved. Restart main.py (or replug the device) to apply.\n")


def main() -> None:
    args = sys.argv[1:]
    values = load_env()
    if not args:
        interactive()
    elif args[0] == "list":
        show(values)
    elif args[0] == "get" and len(args) == 2:
        print(values.get(args[1], ""))
    elif args[0] == "set" and len(args) >= 3:
        values[args[1]] = " ".join(args[2:])
        save_env(values)
        print(f"{args[1]} set.")
    else:
        print("Usage: python settings.py [list | get KEY | set KEY VALUE]")


if __name__ == "__main__":
    main()
