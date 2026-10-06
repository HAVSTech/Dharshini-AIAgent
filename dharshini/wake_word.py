from __future__ import annotations

from pathlib import Path
import numpy as np

FRAME_SAMPLES = 1280  # 80 ms at 16 kHz


class WakeWordDetector:
    """Local, Gemini-free wake-word detector.

    A custom openWakeWord-compatible model can be supplied through
    DHARSHINI_WAKE_MODEL_PATH. Detection happens entirely on the PC.
    """

    def __init__(self, model_path: str, threshold: float = 0.5):
        self.model_path = Path(model_path).expanduser().resolve()
        self.threshold = threshold
        self.model = None

    @property
    def available(self) -> bool:
        return self.model_path.is_file()

    def start(self) -> None:
        if not self.available:
            raise FileNotFoundError(
                f"Wake-word model not found: {self.model_path}"
            )

        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise RuntimeError(
                "openWakeWord is not installed. Run: pip install openwakeword"
            ) from exc

        self.model = Model(wakeword_models=[str(self.model_path)])

    def feed(self, pcm: bytes) -> bool:
        if self.model is None:
            raise RuntimeError("WakeWordDetector.start() must be called first.")

        audio = np.frombuffer(pcm, dtype=np.int16)
        if audio.size == 0:
            return False

        if audio.size < FRAME_SAMPLES:
            audio = np.pad(audio, (0, FRAME_SAMPLES - audio.size))

        triggered = False
        for offset in range(0, len(audio), FRAME_SAMPLES):
            frame = audio[offset : offset + FRAME_SAMPLES]
            if len(frame) < FRAME_SAMPLES:
                frame = np.pad(frame, (0, FRAME_SAMPLES - len(frame)))

            predictions = self.model.predict(frame)
            if not predictions:
                continue

            score = max(float(value) for value in predictions.values())
            if score >= self.threshold:
                triggered = True
                break

        if triggered:
            self.reset()

        return triggered

    def reset(self) -> None:
        if self.model is not None and hasattr(self.model, "reset"):
            self.model.reset()
