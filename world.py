from __future__ import annotations
from copy import deepcopy
from protocol import utc_now


class WorldModel:
    def __init__(self, specification: dict):
        self.specification = deepcopy(specification)
        self.entities = deepcopy(specification["entities"])
        self.needs = {n["id"]: deepcopy(n) for n in specification["agent"]["needs"]}
        self.changed_at = utc_now()

    def get_entity(self, entity_key: str) -> dict:
        if entity_key not in self.entities:
            raise KeyError(f"Неизвестная сущность: {entity_key}")
        return deepcopy(self.entities[entity_key])

    def get_presence(self, entity_key: str) -> str:
        return self.get_entity(entity_key).get("presence", "unknown")

    def set_presence(self, entity_key: str, value: str) -> tuple[str, str]:
        if value not in {"unknown", "present", "absent"}:
            raise ValueError(f"Недопустимое presence: {value}")
        old = self.get_presence(entity_key)
        self.entities[entity_key]["presence"] = value
        self.changed_at = utc_now()
        return old, value

    def active_needs(self) -> list[dict]:
        values = [deepcopy(x) for x in self.needs.values() if not x.get("satisfied", False)]
        return sorted(values, key=lambda x: x.get("priority", 0), reverse=True)

    def satisfy_need(self, need_id: str) -> None:
        if need_id not in self.needs:
            raise KeyError(f"Неизвестная потребность: {need_id}")
        self.needs[need_id]["satisfied"] = True

    def snapshot(self) -> dict:
        return {
            "world_id": self.specification["world_id"],
            "name": self.specification["name"],
            "entities": deepcopy(self.entities),
            "needs": deepcopy(self.needs),
            "changed_at": self.changed_at,
        }
