from __future__ import annotations
import argparse
import json
from pathlib import Path
from config import ConfigError, load_world
from knowledge import KnowledgeBase
from memory import Memory
from monitor import print_summary
from scenario import PresenceScenario
from speech_input import KeyboardInput, MockInput, WhisperMicrophoneInput
from voice import ConsoleVoice, SystemVoice


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Автономная проверка присутствия Владимира")
    p.add_argument("--world", default="world_001.txt")
    p.add_argument("--database", default="aelin_knowledge.db")
    p.add_argument("--events", default="events.jsonl")
    p.add_argument("--mode", choices=("keyboard", "mock", "microphone"), default="keyboard")
    p.add_argument("--answers", default="да,да", help="Ответы mock через запятую")
    p.add_argument("--voice", choices=("console", "system"), default="console")
    p.add_argument("--whisper-model", default="small")
    p.add_argument("--no-wait", action="store_true", help="Не ждать 7 секунд; только для тестов")
    p.add_argument("--show-memory", action="store_true")
    return p


def build_input(args):
    if args.mode == "keyboard":
        return KeyboardInput()
    if args.mode == "mock":
        return MockInput([x.strip() for x in args.answers.split(",")])
    return WhisperMicrophoneInput(model_size=args.whisper_model)


def main() -> int:
    args = parser().parse_args()
    if args.show_memory:
        print_summary(args.database)
        return 0
    kb = None
    input_adapter = None
    voice = None
    try:
        specification = load_world(args.world)
        kb = KnowledgeBase(args.database)
        memory = Memory(kb, args.events)
        input_adapter = build_input(args)
        voice = SystemVoice() if args.voice == "system" else ConsoleVoice()
        scenario = PresenceScenario(
            specification, kb, memory, input_adapter, voice,
            wait_override=0 if args.no_wait else None)
        result = scenario.run()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] == "PASS":
            print("Состояние: PASS")
            return 0
        print("Состояние: ERROR")
        print(result.get("message", ""))
        return 2
    except (ConfigError, RuntimeError) as exc:
        print("Состояние: ERROR")
        print(str(exc))
        return 2
    except KeyboardInterrupt:
        print("\nОстановлено пользователем")
        return 130
    finally:
        if input_adapter:
            input_adapter.close()
        if voice:
            voice.close()
        if kb:
            kb.close()


if __name__ == "__main__":
    raise SystemExit(main())
