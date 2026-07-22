import re
import time
from difflib import SequenceMatcher

import numpy as np

import config
from logger import get_logger

log = get_logger("wake")


class WakeWordDetector:
    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        log.info("Loading wake word model (whisper %s)...", config.WAKE_STT_MODEL)
        self.model = WhisperModel(
            config.WAKE_STT_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
            download_root=str(config.MODELS_DIR),
        )
        self._buf = np.zeros(0, dtype=np.int16)
        self._last_check = 0.0
        log.info("Wake word detector ready — listening for '%s'",
                 config.WAKE_WORD_PHRASE)

    def feed(self, pcm: bytes) -> bool:
        samples = np.frombuffer(pcm, dtype=np.int16)
        self._buf = np.concatenate([self._buf, samples])[-config.SAMPLE_RATE * 3:]
        if len(self._buf) < config.SAMPLE_RATE:
            return False

        now = time.time()
        if now - self._last_check < config.WAKE_CHECK_INTERVAL:
            return False

        recent = self._buf[-config.SAMPLE_RATE:].astype(np.float32)
        rms = float(np.sqrt(np.mean(recent ** 2)))
        if rms < config.VAD_ENERGY_THRESHOLD:
            return False
        self._last_check = now

        audio = self._buf.astype(np.float32) / 32768.0
        segments, _info = self.model.transcribe(
            audio, language="en", beam_size=1, vad_filter=True
        )
        text = " ".join(seg.text for seg in segments).lower()
        text = re.sub(r"[^a-z ]", " ", text)
        if self._matches(text):
            log.info("Wake word detected in: %s", text.strip())
            self.reset()
            return True
        return False

    @staticmethod
    def _matches(text: str) -> bool:
        phrase = config.WAKE_WORD_PHRASE
        if phrase in text:
            return True
        keyword = phrase.split()[-1]
        return any(
            SequenceMatcher(None, word, keyword).ratio() >= config.WAKE_MATCH_RATIO
            for word in text.split()
        )

    def reset(self) -> None:
        self._buf = np.zeros(0, dtype=np.int16)
        self._last_check = 0.0


class UtteranceCapture:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._chunks: list[bytes] = []
        self._started = False
        self._silence_ms = 0.0
        self._total_ms = 0.0

    def feed(self, pcm: bytes) -> bytes | None:
        samples = np.frombuffer(pcm, dtype=np.int16)
        if not len(samples):
            return None
        ms = len(samples) / config.SAMPLE_RATE * 1000
        self._total_ms += ms
        self._chunks.append(pcm)

        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
        if rms >= config.VAD_ENERGY_THRESHOLD:
            self._started = True
            self._silence_ms = 0.0
        elif self._started:
            self._silence_ms += ms

        if not self._started and self._total_ms >= config.VAD_START_TIMEOUT_MS:
            log.info("No speech after wake word — cancelling.")
            self.reset()
            return b""
        if (self._started and self._silence_ms >= config.VAD_SILENCE_MS) or (
            self._total_ms >= config.VAD_MAX_UTTERANCE_MS
        ):
            audio = b"".join(self._chunks)
            log.info("Utterance captured: %.1fs", self._total_ms / 1000)
            self.reset()
            return audio
        return None
