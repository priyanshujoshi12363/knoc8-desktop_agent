import numpy as np

import config
from logger import get_logger

log = get_logger("stt")


class SpeechToText:
    def __init__(self) -> None:
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            log.info("Loading Whisper model '%s'...", config.WHISPER_MODEL)
            self._model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE,
                download_root=str(config.MODELS_DIR),
            )
            log.info("Whisper model ready.")
        return self._model

    def transcribe(self, pcm: bytes) -> str:
        if len(pcm) < config.SAMPLE_RATE // 2:
            return ""
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._ensure_model().transcribe(
            audio,
            language="en",
            vad_filter=True,
            initial_prompt=(
                "Voice commands for a Windows PC assistant: open Chrome, "
                "open Cursor, run npm install, npm run dev, pip install, "
                "git status, git push, mkdir, cd, D drive, C drive, "
                "create a folder, open terminal, VS Code, YouTube, Google."
            ),
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        log.info("Transcript: %s", text or "(silence)")
        return text
