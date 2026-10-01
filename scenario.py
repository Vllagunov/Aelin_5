from __future__ import annotations
import time
from perception import normalize_yes_no, answer_to_presence
from prediction import create_presence_prediction
from protocol import new_id
from question import select_need_and_template
from world import WorldModel


class PresenceScenario:
    def __init__(self, specification: dict, knowledge_base, memory, input_adapter,
                 voice, sleeper=time.sleep, monotonic=time.monotonic,
                 wait_override: float | None = None):
        self.spec = specification
        self.kb = knowledge_base
        self.memory = memory
        self.input = input_adapter
        self.voice = voice
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.wait_override = wait_override
        self.world = WorldModel(specification)

    def _emit(self, kind: str, episode_id: str, module: str, payload: dict | None = None):
        return self.memory.remember(kind, episode_id, module, payload)

    def _ask(self, episode_id: str, entity_key: str, question: str, retry_question: str,
             timeout: float, phase: str) -> tuple[dict, str] | tuple[None, None]:
        for attempt in (1, 2):
            spoken = question if attempt == 1 else retry_question
            self.voice.speak(spoken)
            self._emit("QUESTION_ASKED", episode_id, "voice", {
                "phase": phase, "attempt": attempt, "question": spoken})
            raw = self.input.listen(timeout)
            perception = normalize_yes_no(raw)
            self._emit("ANSWER_RECOGNIZED", episode_id, "perception", {
                "phase": phase, "attempt": attempt, **perception})
            if perception["normalized_answer"] != "unknown" and perception["confidence"] >= 0.60:
                presence = answer_to_presence(perception["normalized_answer"])
                return perception, presence
        return None, None

    def run(self) -> dict:
        episode_id = new_id("episode")
        need, template_name, template = select_need_and_template(self.spec)
        entity_key = template["entity"]
        question = template["question"]
        retry = template.get("retry_question", question)
        timeout = float(template.get("answer_timeout_seconds", 5))
        configured_horizon = float(template["repeat_after_seconds"])
        actual_wait = configured_horizon if self.wait_override is None else float(self.wait_override)
        rule = template.get("prediction_rule", "presence_remains_unchanged")
        self.kb.bootstrap(self.spec)
        self.kb.ensure_prediction_rule(rule, configured_horizon)
        self.kb.start_episode(episode_id, template_name, self.spec["world_id"], self.world.snapshot())
        self._emit("WORLD_LOADED", episode_id, "scenario", {"world_id": self.spec["world_id"]})
        self.kb.snapshot(episode_id, "initial", self.world.snapshot())
        try:
            self._emit("NEED_SELECTED", episode_id, "scenario", {"need": need["id"]})
            self._emit("ACTION_SELECTED", episode_id, "scenario", {"template": template_name})
            first, first_presence = self._ask(
                episode_id, entity_key, question, retry, timeout, "first")
            if first is None:
                self._emit("SCENARIO_ERROR", episode_id, "scenario", {
                    "code": "FIRST_ANSWER_UNKNOWN", "message": "Первый ответ не распознан"})
                self.kb.finish_episode(episode_id, "error", self.world.snapshot(), "Первый ответ не распознан")
                return {"status": "ERROR", "episode_id": episode_id,
                        "message": "Первый ответ не распознан; мир не изменён"}
            old = self.world.get_presence(entity_key)
            self.kb.record_observation_and_fact(
                episode_id, entity_key, "first", question, first, first_presence)
            self.world.set_presence(entity_key, first_presence)
            self.world.satisfy_need(need["id"])
            self._emit("WORLD_CHANGED", episode_id, "world", {
                "entity": entity_key, "property": "presence", "old_value": old,
                "new_value": first_presence, "source": "answer", "confidence": first["confidence"]})
            prediction = create_presence_prediction(
                episode_id, entity_key, first_presence, configured_horizon, rule)
            self.kb.create_prediction(prediction)
            self._emit("PREDICTION_CREATED", episode_id, "prediction", prediction)
            started = self.monotonic()
            if actual_wait > 0:
                self.sleeper(max(0.0, actual_wait - (self.monotonic() - started)))
            self._emit("PREDICTION_DUE", episode_id, "scenario", {
                "prediction_id": prediction["prediction_id"],
                "configured_horizon_seconds": configured_horizon,
                "actual_wait_seconds": actual_wait})
            second, second_presence = self._ask(
                episode_id, entity_key, question, retry, timeout, "second")
            if second is None:
                prediction_status = self.kb.check_prediction(prediction["prediction_id"], None)
                self._emit("PREDICTION_CHECKED", episode_id, "prediction", {
                    "prediction_id": prediction["prediction_id"], "status": prediction_status,
                    "observed_value": None})
            else:
                old = self.world.get_presence(entity_key)
                self.kb.record_observation_and_fact(
                    episode_id, entity_key, "second", question, second, second_presence)
                self.world.set_presence(entity_key, second_presence)
                self._emit("WORLD_CHANGED", episode_id, "world", {
                    "entity": entity_key, "property": "presence", "old_value": old,
                    "new_value": second_presence, "source": "answer", "confidence": second["confidence"]})
                prediction_status = self.kb.check_prediction(
                    prediction["prediction_id"], second_presence)
                self._emit("PREDICTION_CHECKED", episode_id, "prediction", {
                    "prediction_id": prediction["prediction_id"], "status": prediction_status,
                    "predicted_value": prediction["predicted_value"],
                    "observed_value": second_presence})
            final_world = self.world.snapshot()
            self.kb.snapshot(episode_id, "final", final_world)
            self.kb.finish_episode(episode_id, "completed", final_world)
            self._emit("SCENARIO_COMPLETED", episode_id, "scenario", {
                "prediction_status": prediction_status})
            return {
                "status": "PASS", "episode_id": episode_id,
                "first_presence": first_presence,
                "second_presence": second_presence,
                "current_presence": self.world.get_presence(entity_key),
                "prediction_status": prediction_status,
                "prediction_id": prediction["prediction_id"],
            }
        except Exception as exc:
            try:
                self._emit("SCENARIO_ERROR", episode_id, "scenario", {
                    "code": type(exc).__name__, "message": str(exc)})
                self.kb.finish_episode(episode_id, "error", self.world.snapshot(), str(exc))
            finally:
                raise
