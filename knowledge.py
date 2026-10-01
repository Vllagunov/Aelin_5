from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from protocol import utc_now

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS entities(
 id INTEGER PRIMARY KEY, entity_key TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 entity_type TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS episodes(
 episode_id TEXT PRIMARY KEY, scenario TEXT NOT NULL, world_id TEXT NOT NULL,
 started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL,
 initial_world_json TEXT NOT NULL, final_world_json TEXT, error_text TEXT);
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT, episode_id TEXT NOT NULL,
 event_type TEXT NOT NULL, timestamp TEXT NOT NULL, module TEXT NOT NULL,
 payload_json TEXT NOT NULL, FOREIGN KEY(episode_id) REFERENCES episodes(episode_id));
CREATE TABLE IF NOT EXISTS facts(
 id INTEGER PRIMARY KEY AUTOINCREMENT, entity_key TEXT NOT NULL,
 property TEXT NOT NULL, value TEXT NOT NULL, confidence REAL NOT NULL,
 source TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT,
 is_current INTEGER NOT NULL, episode_id TEXT NOT NULL,
 FOREIGN KEY(episode_id) REFERENCES episodes(episode_id));
CREATE INDEX IF NOT EXISTS ix_current_facts ON facts(entity_key, property, is_current);
CREATE TABLE IF NOT EXISTS observations(
 id INTEGER PRIMARY KEY AUTOINCREMENT, episode_id TEXT NOT NULL,
 entity_key TEXT NOT NULL, phase TEXT NOT NULL, question TEXT NOT NULL,
 raw_answer TEXT NOT NULL, normalized_answer TEXT NOT NULL,
 conclusion TEXT NOT NULL, confidence REAL NOT NULL, observed_at TEXT NOT NULL,
 FOREIGN KEY(episode_id) REFERENCES episodes(episode_id));
CREATE TABLE IF NOT EXISTS predictions(
 prediction_id TEXT PRIMARY KEY, episode_id TEXT NOT NULL, entity_key TEXT NOT NULL,
 property TEXT NOT NULL, predicted_value TEXT NOT NULL, confidence REAL NOT NULL,
 rule TEXT NOT NULL, horizon_seconds REAL NOT NULL, created_at TEXT NOT NULL,
 due_at TEXT NOT NULL, checked_at TEXT, observed_value TEXT, status TEXT NOT NULL,
 FOREIGN KEY(episode_id) REFERENCES episodes(episode_id));
CREATE TABLE IF NOT EXISTS action_templates(
 template_key TEXT PRIMARY KEY, need_id TEXT NOT NULL, question TEXT NOT NULL,
 repeat_after_seconds REAL NOT NULL, prediction_rule TEXT NOT NULL,
 configuration_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge_rules(
 rule_key TEXT PRIMARY KEY, description TEXT NOT NULL, confirmations INTEGER NOT NULL DEFAULT 0,
 contradictions INTEGER NOT NULL DEFAULT 0, confidence REAL NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots(
 id INTEGER PRIMARY KEY AUTOINCREMENT, episode_id TEXT NOT NULL,
 phase TEXT NOT NULL, created_at TEXT NOT NULL, world_json TEXT NOT NULL,
 FOREIGN KEY(episode_id) REFERENCES episodes(episode_id));
"""


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class KnowledgeBase:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def bootstrap(self, specification: dict) -> None:
        now = utc_now()
        with self.conn:
            for key, item in specification["entities"].items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO entities(entity_key,name,entity_type,created_at) VALUES(?,?,?,?)",
                    (key, item.get("name", key), item.get("type", "unknown"), now))
            for key, item in specification["action_templates"].items():
                self.conn.execute(
                    """INSERT INTO action_templates(template_key,need_id,question,repeat_after_seconds,
                    prediction_rule,configuration_json) VALUES(?,?,?,?,?,?)
                    ON CONFLICT(template_key) DO UPDATE SET need_id=excluded.need_id,
                    question=excluded.question,repeat_after_seconds=excluded.repeat_after_seconds,
                    prediction_rule=excluded.prediction_rule,configuration_json=excluded.configuration_json""",
                    (key, item["need"], item["question"], float(item["repeat_after_seconds"]),
                     item.get("prediction_rule", "presence_remains_unchanged"), dumps(item)))
            for key, description in specification.get("knowledge_rules", []):
                self.conn.execute(
                    "INSERT OR IGNORE INTO knowledge_rules(rule_key,description,updated_at) VALUES(?,?,?)",
                    (key, description, now))

    def start_episode(self, episode_id: str, scenario: str, world_id: str, initial_world: dict) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?,?)",
                (episode_id, scenario, world_id, utc_now(), None, "running", dumps(initial_world), None, None))

    def add_event(self, item: dict) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO events(episode_id,event_type,timestamp,module,payload_json) VALUES(?,?,?,?,?)",
                (item["episode_id"], item["type"], item["timestamp"], item["module"], dumps(item["payload"])))

    def snapshot(self, episode_id: str, phase: str, world: dict) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO snapshots(episode_id,phase,created_at,world_json) VALUES(?,?,?,?)",
                (episode_id, phase, utc_now(), dumps(world)))

    def record_observation_and_fact(self, episode_id: str, entity_key: str, phase: str,
                                    question: str, perception: dict, presence: str,
                                    source: str = "answer") -> None:
        now = utc_now()
        with self.conn:
            self.conn.execute(
                """INSERT INTO observations(episode_id,entity_key,phase,question,raw_answer,
                normalized_answer,conclusion,confidence,observed_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (episode_id, entity_key, phase, question, perception["raw_text"],
                 perception["normalized_answer"], presence, float(perception["confidence"]), now))
            self.conn.execute(
                "UPDATE facts SET valid_to=?,is_current=0 WHERE entity_key=? AND property='presence' AND is_current=1",
                (now, entity_key))
            self.conn.execute(
                """INSERT INTO facts(entity_key,property,value,confidence,source,valid_from,
                valid_to,is_current,episode_id) VALUES(?,?,?,?,?,?,?,?,?)""",
                (entity_key, "presence", presence, float(perception["confidence"]), source,
                 now, None, 1, episode_id))

    def create_prediction(self, prediction: dict) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT INTO predictions(prediction_id,episode_id,entity_key,property,predicted_value,
                confidence,rule,horizon_seconds,created_at,due_at,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (prediction["prediction_id"], prediction["episode_id"], prediction["entity_key"],
                 prediction["property"], prediction["predicted_value"], prediction["confidence"],
                 prediction["rule"], prediction["horizon_seconds"], prediction["created_at"],
                 prediction["due_at"], "pending"))

    def check_prediction(self, prediction_id: str, observed_value: str | None) -> str:
        row = self.conn.execute(
            "SELECT predicted_value,rule FROM predictions WHERE prediction_id=?", (prediction_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Прогноз не найден: {prediction_id}")
        if observed_value is None:
            status = "inconclusive"
        else:
            status = "confirmed" if row["predicted_value"] == observed_value else "contradicted"
        now = utc_now()
        with self.conn:
            self.conn.execute(
                "UPDATE predictions SET checked_at=?,observed_value=?,status=? WHERE prediction_id=?",
                (now, observed_value, status, prediction_id))
            if status in {"confirmed", "contradicted"}:
                column = "confirmations" if status == "confirmed" else "contradictions"
                self.conn.execute(
                    f"UPDATE knowledge_rules SET {column}={column}+1,updated_at=? WHERE rule_key=?",
                    (now, row["rule"]))
                counts = self.conn.execute(
                    "SELECT confirmations,contradictions FROM knowledge_rules WHERE rule_key=?",
                    (row["rule"],)).fetchone()
                if counts:
                    total = counts[0] + counts[1]
                    confidence = counts[0] / total if total else 0.0
                    self.conn.execute(
                        "UPDATE knowledge_rules SET confidence=? WHERE rule_key=?",
                        (confidence, row["rule"]))
        return status

    def ensure_prediction_rule(self, rule: str, horizon: float) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO knowledge_rules(rule_key,description,updated_at) VALUES(?,?,?)",
                (rule, f"Состояние присутствия сохраняется в течение {horizon:g} секунд", utc_now()))

    def finish_episode(self, episode_id: str, status: str, final_world: dict,
                       error_text: str | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE episodes SET completed_at=?,status=?,final_world_json=?,error_text=? WHERE episode_id=?",
                (utc_now(), status, dumps(final_world), error_text, episode_id))

    def current_fact(self, entity_key: str, prop: str = "presence") -> dict | None:
        row = self.conn.execute(
            """SELECT * FROM facts WHERE entity_key=? AND property=? AND is_current=1
            ORDER BY id DESC LIMIT 1""", (entity_key, prop)).fetchone()
        return dict(row) if row else None

    def summary(self) -> dict:
        result = {}
        for table in ("episodes", "events", "facts", "observations", "predictions", "knowledge_rules"):
            result[table] = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return result

    def close(self) -> None:
        self.conn.close()
