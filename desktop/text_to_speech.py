import subprocess
import sys
import uuid
import wave

import numpy as np

import config
from logger import get_logger

log = get_logger("tts")


class TextToSpeech:
    def synthesize(self, text: str) -> bytes:
        wav_path = config.AUDIO_DIR / f"tts_{uuid.uuid4().hex}.wav"
        try:
            self._render_wav(text, str(wav_path))
            return self._wav_to_pcm(str(wav_path))
        finally:
            wav_path.unlink(missing_ok=True)

    @staticmethod
    def _script(text: str) -> str:
        return (
            "import pyttsx3\n"
            "e = pyttsx3.init()\n"
            f"e.setProperty('rate', {config.TTS_RATE})\n"
            f"e.say({text!r})\n"
            "e.runAndWait()\n"
        )

    def speak_local(self, text: str) -> None:
        try:
            subprocess.run(
                [sys.executable, "-c", self._script(text)],
                timeout=60,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            log.warning("TTS subprocess timed out — killed, continuing.")

    def speak_local_async(self, text: str) -> subprocess.Popen:
        return subprocess.Popen(
            [sys.executable, "-c", self._script(text)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    @staticmethod
    def _render_wav(text: str, path: str) -> None:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", config.TTS_RATE)
        engine.save_to_file(text, path)
        engine.runAndWait()
        engine.stop()

    @staticmethod
    def _wav_to_pcm(path: str) -> bytes:
        with wave.open(path, "rb") as wav:
            rate = wav.getframerate()
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            frames = wav.readframes(wav.getnframes())

        if width != 2:
            raise ValueError(f"Unsupported sample width: {width}")
        samples = np.frombuffer(frames, dtype=np.int16)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)
        if rate != config.SAMPLE_RATE:
            n_out = int(len(samples) * config.SAMPLE_RATE / rate)
            x_old = np.linspace(0, 1, len(samples), endpoint=False)
            x_new = np.linspace(0, 1, n_out, endpoint=False)
            samples = np.interp(x_new, x_old, samples).astype(np.int16)
        log.debug("TTS audio: %.1fs", len(samples) / config.SAMPLE_RATE)
        return samples.tobytes()
