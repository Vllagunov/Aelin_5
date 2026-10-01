def select_need_and_template(specification: dict) -> tuple[dict, str, dict]:
    needs = [n for n in specification["agent"]["needs"] if not n.get("satisfied", False)]
    if not needs:
        raise RuntimeError("Нет активных потребностей")
    need = sorted(needs, key=lambda x: x.get("priority", 0), reverse=True)[0]
    abilities = set(specification["agent"].get("abilities", []))
    for name, template in specification["action_templates"].items():
        if template.get("need") != need["id"]:
            continue
        missing = set(template.get("required_abilities", [])) - abilities
        if missing:
            raise RuntimeError("Не хватает способностей: " + ", ".join(sorted(missing)))
        return need, name, template
    raise RuntimeError(f"Не найден шаблон для потребности {need['id']}")
