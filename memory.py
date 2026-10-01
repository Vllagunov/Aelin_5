from __future__ import annotations
import json
from pathlib import Path
from protocol import event


class Memory:
    def __init__(self, knowledge_base, jsonl_path: str | Path | None = None):
        self.kb = knowledge_base
        self.current_events = []
        self.jsonl_path = Path(jsonl_path) if jsonl_path else None
        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def remember(self, event_type: str, episode_id: str, module: str, payload: dict | None = None) -> dict:
        item = event(event_type, episode_id, module, payload)
        self.current_events.append(item)
        self.kb.add_event(item)
        if self.jsonl_path:
            with self.jsonl_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item
