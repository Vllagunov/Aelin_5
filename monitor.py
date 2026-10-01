from __future__ import annotations
import json
from knowledge import KnowledgeBase


def print_summary(database_path: str) -> None:
    kb = KnowledgeBase(database_path)
    try:
        print(json.dumps(kb.summary(), ensure_ascii=False, indent=2))
        fact = kb.current_fact("vladimir")
        if fact:
            print("Текущий факт:")
            print(json.dumps(fact, ensure_ascii=False, indent=2))
        else:
            print("Текущих фактов о Владимире пока нет.")
    finally:
        kb.close()
