from __future__ import annotations


class ConsoleVoice:
    def speak(self, text: str) -> None:
        print(f"Система: {text}", flush=True)

    def close(self) -> None:
        pass


class SystemVoice(ConsoleVoice):
    def __init__(self, rate: int = 175):
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("Для голоса установите: pip install pyttsx3") from exc
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)

    def speak(self, text: str) -> None:
        print(f"Система: {text}", flush=True)
        self.engine.say(text)
        self.engine.runAndWait()

    def close(self) -> None:
        self.engine.stop()
