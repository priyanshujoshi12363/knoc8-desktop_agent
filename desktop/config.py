import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SERIAL_PORT: str = os.getenv("KNOC8_SERIAL_PORT", "COM5")
SERIAL_BAUDRATE: int = int(os.getenv("KNOC8_SERIAL_BAUD", "921600"))
SERIAL_TIMEOUT: float = 0.1
SERIAL_AUDIO_CHUNK: int = 1024

SAMPLE_RATE: int = 16000
SAMPLE_WIDTH: int = 2
CHANNELS: int = 1

AUDIO_DIR = BASE_DIR / "audio"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
MEMORY_FILE = BASE_DIR / "memory.json"

LLM_PROVIDER: str = os.getenv("KNOC8_LLM_PROVIDER", "ollama").lower()
LLM_TIMEOUT: int = 120
LLM_HISTORY_TURNS: int = 10
LLM_MAX_TOKENS: int = int(os.getenv("KNOC8_LLM_MAX_TOKENS", "2048"))

# Ollama Cloud
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
LLM_MODEL: str = os.getenv("KNOC8_LLM_MODEL", "minimax-m3")

# Anthropic (Claude)
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("KNOC8_ANTHROPIC_MODEL", "claude-opus-4-8")

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("KNOC8_OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

WHISPER_MODEL: str = os.getenv("KNOC8_WHISPER_MODEL", "base")
def _pick_device() -> tuple[str, str]:
    """Use the GPU when one is actually usable, otherwise CPU int8."""
    want = os.getenv("KNOC8_WHISPER_DEVICE", "auto").lower()
    if want in ("cpu", "cuda"):
        return want, os.getenv(
            "KNOC8_WHISPER_COMPUTE", "float16" if want == "cuda" else "int8")
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", os.getenv("KNOC8_WHISPER_COMPUTE", "float16")
    except Exception:
        pass
    return "cpu", os.getenv("KNOC8_WHISPER_COMPUTE", "int8")


WHISPER_DEVICE, WHISPER_COMPUTE = _pick_device()

TTS_RATE: int = int(os.getenv("KNOC8_TTS_RATE", "175"))

# Hold-to-talk: recording starts on button down and ends on button up.
MIN_HOLD_MS: int = int(os.getenv("KNOC8_MIN_HOLD_MS", "400"))
MAX_HOLD_MS: int = int(os.getenv("KNOC8_MAX_HOLD_MS", "30000"))

CHROME_PROFILE: str = os.getenv("KNOC8_CHROME_PROFILE", "")

# Coding agent used by the `coding` tool ("" = auto-detect)
CODING_AGENT: str = os.getenv("KNOC8_CODING_AGENT", "")

NOISE_REDUCTION: bool = os.getenv("KNOC8_NOISE_REDUCTION", "1") != "0"

SETTINGS_PORT: int = int(os.getenv("KNOC8_SETTINGS_PORT", "8733"))

MAX_PLAN_STEPS: int = 20
ASSISTANT_NAME: str = "Knoc8"

# Safety
SAFE_MODE: bool = os.getenv("KNOC8_SAFE_MODE", "1") != "0"
CONFIRM_TIMEOUT: int = int(os.getenv("KNOC8_CONFIRM_TIMEOUT", "20"))
DELETE_TO_RECYCLE_BIN: bool = os.getenv("KNOC8_RECYCLE_BIN", "1") != "0"

for _d in (AUDIO_DIR, MODELS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
