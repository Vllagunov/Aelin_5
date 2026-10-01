from __future__ import annotations
import json
from pathlib import Path

PRESENCE_VALUES = {"unknown", "present", "absent"}
HOSTILITY_VALUES = {"unknown", "friendly", "neutral", "hostile"}
REQUIRED_ABILITIES = {
    "speak", "listen", "recognize_yes_no", "change_world",
    "make_prediction", "wait", "remember"
}


class ConfigError(ValueError):
    pass


def load_world(path: str | Path) -> dict:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Файл мира не найден: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Ошибка JSON в {path}, строка {exc.lineno}: {exc.msg}") from exc
    validate_world(data)
    return data


def validate_world(data: dict) -> None:
    for key in ("world_id", "name", "entities", "agent", "action_templates"):
        if key not in data:
            raise ConfigError(f"В описании мира отсутствует поле: {key}")
    if not isinstance(data["entities"], dict) or not data["entities"]:
        raise ConfigError("entities должен быть непустым объектом")
    for entity_key, entity in data["entities"].items():
        if entity.get("presence", "unknown") not in PRESENCE_VALUES:
            raise ConfigError(f"Недопустимое presence у {entity_key}")
        if entity.get("hostility", "unknown") not in HOSTILITY_VALUES:
            raise ConfigError(f"Недопустимое hostility у {entity_key}")
    abilities = set(data["agent"].get("abilities", []))
    missing = REQUIRED_ABILITIES - abilities
    if missing:
        raise ConfigError("Не хватает способностей: " + ", ".join(sorted(missing)))
    needs = {n.get("id") for n in data["agent"].get("needs", [])}
    if not needs:
        raise ConfigError("Не задано ни одной потребности")
    for name, template in data["action_templates"].items():
        for key in ("need", "entity", "question", "repeat_after_seconds"):
            if key not in template:
                raise ConfigError(f"В шаблоне {name} отсутствует поле {key}")
        if template["need"] not in needs:
            raise ConfigError(f"Шаблон {name} ссылается на неизвестную потребность")
        if template["entity"] not in data["entities"]:
            raise ConfigError(f"Шаблон {name} ссылается на неизвестную сущность")
        if float(template["repeat_after_seconds"]) < 0:
            raise ConfigError("repeat_after_seconds не может быть отрицательным")
