import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SERIAL_PORT: str = os.getenv("KNOC8_SERIAL_PORT", "COM16")
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

OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
LLM_MODEL: str = os.getenv("KNOC8_LLM_MODEL", "minimax-m3")
LLM_TIMEOUT: int = 120
LLM_HISTORY_TURNS: int = 10

WHISPER_MODEL: str = os.getenv("KNOC8_WHISPER_MODEL", "base")
WHISPER_DEVICE: str = "cpu"
WHISPER_COMPUTE: str = "int8"

TTS_RATE: int = int(os.getenv("KNOC8_TTS_RATE", "175"))

WAKE_WORD_PHRASE: str = os.getenv("KNOC8_WAKE_WORD", "hey agent").lower()
WAKE_STT_MODEL: str = os.getenv("KNOC8_WAKE_MODEL", "tiny")
WAKE_CHECK_INTERVAL: float = 0.8
WAKE_MATCH_RATIO: float = 0.85
VAD_ENERGY_THRESHOLD: int = int(os.getenv("KNOC8_MIC_THRESHOLD", "300"))
VAD_SILENCE_MS: int = int(os.getenv("KNOC8_SILENCE_MS", "1200"))
VAD_START_TIMEOUT_MS: int = 5000
VAD_MAX_UTTERANCE_MS: int = 15000

CHROME_PROFILE: str = os.getenv("KNOC8_CHROME_PROFILE", "")

NOISE_REDUCTION: bool = os.getenv("KNOC8_NOISE_REDUCTION", "1") != "0"

MAX_PLAN_STEPS: int = 20
ASSISTANT_NAME: str = "Knoc8"

for _d in (AUDIO_DIR, MODELS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
