import numpy as np

import config
from logger import get_logger

log = get_logger("dsp")


class HighPassFilter:
    def __init__(self, cutoff_hz: float = 100.0) -> None:
        from scipy.signal import butter, lfilter_zi

        self._b, self._a = butter(2, cutoff_hz / (config.SAMPLE_RATE / 2), "highpass")
        self._zi = lfilter_zi(self._b, self._a) * 0.0

    def process(self, pcm: bytes) -> bytes:
        from scipy.signal import lfilter

        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        if not len(x):
            return pcm
        y, self._zi = lfilter(self._b, self._a, x, zi=self._zi)
        return np.clip(y, -32768, 32767).astype(np.int16).tobytes()


def denoise_utterance(pcm: bytes) -> bytes:
    if not config.NOISE_REDUCTION or len(pcm) < config.SAMPLE_RATE:
        return pcm
    try:
        import noisereduce as nr

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        cleaned = nr.reduce_noise(
            y=audio,
            sr=config.SAMPLE_RATE,
            stationary=True,
            prop_decrease=0.85,
        )
        log.debug("Denoised %.1fs of audio", len(audio) / config.SAMPLE_RATE)
        return (np.clip(cleaned, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    except Exception as exc:
        log.warning("Noise reduction failed, using raw audio: %s", exc)
        return pcm
