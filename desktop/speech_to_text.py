import numpy as np
import time

import config
from logger import get_logger

log = get_logger("stt")

_PROMPT = (
    "Voice commands for a Windows PC assistant: open Chrome, "
    "open Cursor, run npm install, npm run dev, pip install, "
    "git status, git push, mkdir, cd, D drive, C drive, "
    "create a folder, open terminal, VS Code, YouTube, Google, "
    "backend, Snake game, executable, EXE, PyInstaller, Python, React."
)


class SpeechToText:
    def __init__(self) -> None:
        self._model = None
        self.device = config.WHISPER_DEVICE
        self.compute = config.WHISPER_COMPUTE

    def _load(self, device: str, compute: str):
        from faster_whisper import WhisperModel

        log.info("Loading Whisper model '%s' on %s (%s)...",
                 config.WHISPER_MODEL, device, compute)
        model = WhisperModel(
            config.WHISPER_MODEL,
            device=device,
            compute_type=compute,
            download_root=str(config.MODELS_DIR),
        )
        # A CUDA model can load fine and still die on the first real
        # transcription when the CUDA runtime DLLs (cuBLAS/cuDNN) are
        # missing. Run one tiny inference now so that failure happens at
        # startup, where we can fall back, not mid-command.
        segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32),
                                       language="en")
        list(segments)
        return model

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        try:
            self._model = self._load(self.device, self.compute)
        except Exception as exc:
            if self.device == "cpu":
                raise
            log.warning("Whisper on %s failed (%s) - falling back to CPU.",
                        self.device, exc)
            self.device, self.compute = "cpu", "int8"
            self._model = self._load(self.device, self.compute)
        log.info("Whisper model ready on %s.", self.device)
        return self._model

    def preload(self) -> None:
        """Load (and on first run, download) the model up front."""
        self._ensure_model()

    def transcribe(self, pcm: bytes) -> str:
        started = time.perf_counter()
        if len(pcm) < config.SAMPLE_RATE // 2:
            return ""
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        try:
            text = self._run(audio)
        except Exception as exc:
            if self.device == "cpu":
                raise
            # Belt and braces: GPU died mid-session - switch to CPU and retry.
            log.warning("Transcription on %s failed (%s) - retrying on CPU.",
                        self.device, exc)
            self._model = None
            self.device, self.compute = "cpu", "int8"
            text = self._run(audio)
        log.info("Transcript: %s", text or "(silence)")
        log.info("STT %.2fs on %s for %.2fs audio", time.perf_counter() - started,
                 self.device, len(audio) / config.SAMPLE_RATE)
        return text

    def _run(self, audio: np.ndarray) -> str:
        segments, _info = self._ensure_model().transcribe(
            audio, language=None if config.WHISPER_LANGUAGE == "auto" else config.WHISPER_LANGUAGE,
            vad_filter=True, initial_prompt=_PROMPT,
            beam_size=config.WHISPER_BEAM_SIZE, temperature=0.0,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
