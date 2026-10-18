"""Hold-to-talk capture.

The device streams PCM only while the button is physically held, so there is
no silence detection and no energy threshold involved in ending a recording —
the user decides when it stops by letting go.

Mic level is tracked purely so the console can tell you when the microphone
is producing (near-)silence, which is otherwise invisible.
"""

import numpy as np

import config
from logger import get_logger

log = get_logger("capture")

# Below this peak RMS the audio is almost certainly silence / a dead mic.
QUIET_RMS = 120.0


class HoldCapture:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._chunks: list[bytes] = []
        self._total_ms = 0.0
        self._peak_rms = 0.0
        self._sum_sq = 0.0
        self._samples = 0

    def feed(self, pcm: bytes) -> bool:
        """Accumulate audio. Returns False once the maximum hold is reached."""
        samples = np.frombuffer(pcm, dtype=np.int16)
        if not len(samples):
            return True
        self._chunks.append(pcm)
        self._total_ms += len(samples) / config.SAMPLE_RATE * 1000

        block = samples.astype(np.float32)
        rms = float(np.sqrt(np.mean(block ** 2)))
        self._peak_rms = max(self._peak_rms, rms)
        self._sum_sq += float(np.sum(block ** 2))
        self._samples += len(block)

        return self._total_ms < config.MAX_HOLD_MS

    def finish(self) -> bytes:
        audio = b"".join(self._chunks)
        log.info("Captured %.1fs, peak RMS %.0f, avg RMS %.0f",
                 self._total_ms / 1000, self._peak_rms, self.average_rms)
        return audio

    @property
    def duration_ms(self) -> float:
        return self._total_ms

    @property
    def peak_rms(self) -> float:
        return self._peak_rms

    @property
    def average_rms(self) -> float:
        if not self._samples:
            return 0.0
        return float(np.sqrt(self._sum_sq / self._samples))

    @property
    def too_short(self) -> bool:
        return self._total_ms < config.MIN_HOLD_MS

    @property
    def too_quiet(self) -> bool:
        return self._peak_rms < QUIET_RMS

    def level_note(self) -> str:
        """Human-readable mic level, shown in the console after each capture."""
        return (f"{self._total_ms / 1000:.1f}s, level {self._peak_rms:.0f}"
                f" (speech is usually 500+)")
