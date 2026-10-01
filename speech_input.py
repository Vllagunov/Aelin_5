from __future__ import annotations
from collections import deque
from pathlib import Path
import tempfile
import wave


class KeyboardInput:
    def listen(self, timeout_seconds: float = 5) -> str:
        return input("Ваш ответ: ").strip()

    def close(self) -> None:
        pass


class MockInput:
    def __init__(self, answers: list[str]):
        self.answers = deque(answers)

    def listen(self, timeout_seconds: float = 5) -> str:
        answer = self.answers.popleft() if self.answers else ""
        print(f"Тестовый ответ: {answer!r}", flush=True)
        return answer

    def close(self) -> None:
        pass


class WhisperMicrophoneInput:
    def __init__(self, model_size: str = "small", language: str = "ru", sample_rate: int = 16000):
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "Для режима microphone установите зависимости из requirements-voice.txt"
            ) from exc
        self.np = np
        self.sd = sd
        self.sample_rate = sample_rate
        self.language = language
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def listen(self, timeout_seconds: float = 5) -> str:
        seconds = max(1.0, float(timeout_seconds))
        print(f"Слушаю {seconds:g} сек...", flush=True)
        recording = self.sd.rec(
            int(seconds * self.sample_rate), samplerate=self.sample_rate,
            channels=1, dtype="int16"
        )
        self.sd.wait()
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = Path(tmp.name)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate)
                wav.writeframes(recording.tobytes())
            segments, _ = self.model.transcribe(
                str(path), language=self.language, vad_filter=True, beam_size=3
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            print(f"Распознано: {text!r}", flush=True)
            return text
        finally:
            if path:
                path.unlink(missing_ok=True)

    def close(self) -> None:
        pass
