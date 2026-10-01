from __future__ import annotations
import re

YES_PHRASES = {
    "да", "ага", "угу", "здесь", "я здесь", "да я здесь",
    "конечно", "присутствую", "да здесь"
}
NO_PHRASES = {
    "нет", "не здесь", "меня нет", "его нет", "владимира нет",
    "отсутствует", "нет меня здесь нет"
}


def clean_text(text: str | None) -> str:
    value = (text or "").casefold().replace("ё", "е")
    value = re.sub(r"[^а-яa-z0-9\s-]", " ", value)
    return " ".join(value.split())


def normalize_yes_no(text: str | None) -> dict:
    cleaned = clean_text(text)
    if not cleaned:
        return {"raw_text": text or "", "normalized_answer": "unknown", "confidence": 0.0}
    if cleaned in NO_PHRASES or re.search(r"\b(не здесь|владимира нет|его нет|отсутствует)\b", cleaned):
        answer, confidence = "no", 0.98
    elif cleaned in YES_PHRASES or re.search(r"\b(да|ага|угу|присутствую)\b", cleaned):
        answer, confidence = "yes", 0.96
    elif cleaned == "здесь" or cleaned.endswith(" я здесь"):
        answer, confidence = "yes", 0.90
    elif cleaned == "нет":
        answer, confidence = "no", 0.98
    else:
        answer, confidence = "unknown", 0.20
    return {"raw_text": text or "", "normalized_answer": answer, "confidence": confidence}


def answer_to_presence(normalized_answer: str) -> str:
    mapping = {"yes": "present", "no": "absent"}
    if normalized_answer not in mapping:
        raise ValueError("Нельзя изменить мир по неопределённому ответу")
    return mapping[normalized_answer]
