from __future__ import annotations
import json
import sqlite3
import tempfile
from pathlib import Path
from config import load_world
from knowledge import KnowledgeBase
from memory import Memory
from perception import normalize_yes_no
from scenario import PresenceScenario
from speech_input import MockInput
from voice import ConsoleVoice


def main() -> int:
    checks = []
    spec = load_world("world_001.txt")
    checks.append(("world_config", True))
    checks.append(("normalize_yes", normalize_yes_no("Да, я здесь")["normalized_answer"] == "yes"))
    checks.append(("normalize_no", normalize_yes_no("Владимира нет")["normalized_answer"] == "no"))
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        kb = KnowledgeBase(db_path)
        try:
            scenario = PresenceScenario(
                spec, kb, Memory(kb), MockInput(["да", "да"]), ConsoleVoice(), wait_override=0)
            result = scenario.run()
            checks.append(("scenario", result["status"] == "PASS"))
            checks.append(("prediction", result["prediction_status"] == "confirmed"))
            checks.append(("database", kb.summary()["observations"] == 2))
        finally:
            kb.close()
    print(json.dumps(dict(checks), ensure_ascii=False, indent=2))
    passed = all(value for _, value in checks)
    print("Модуль автономных вопросов готов к работе." if passed else "Состояние: ERROR")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
