import tempfile
import unittest
from pathlib import Path
from config import load_world
from knowledge import KnowledgeBase
from memory import Memory
from scenario import PresenceScenario
from speech_input import MockInput
from voice import ConsoleVoice

ROOT = Path(__file__).resolve().parents[1]


class SystemTests(unittest.TestCase):
    def run_case(self, answers):
        with tempfile.TemporaryDirectory() as tmp:
            kb = KnowledgeBase(Path(tmp) / "test.db")
            try:
                scenario = PresenceScenario(
                    load_world(ROOT / "world_001.txt"), kb, Memory(kb),
                    MockInput(answers), ConsoleVoice(), wait_override=0)
                result = scenario.run()
                summary = kb.summary()
                fact = kb.current_fact("vladimir")
                return result, summary, fact
            finally:
                kb.close()

    def test_yes_yes_confirmed(self):
        result, summary, fact = self.run_case(["да", "да"])
        self.assertEqual(result["prediction_status"], "confirmed")
        self.assertEqual(fact["value"], "present")
        self.assertEqual(summary["observations"], 2)

    def test_yes_no_contradicted(self):
        result, _, fact = self.run_case(["да", "нет"])
        self.assertEqual(result["prediction_status"], "contradicted")
        self.assertEqual(fact["value"], "absent")

    def test_no_no_confirmed(self):
        result, _, fact = self.run_case(["нет", "нет"])
        self.assertEqual(result["prediction_status"], "confirmed")
        self.assertEqual(fact["value"], "absent")

    def test_no_yes_contradicted(self):
        result, _, fact = self.run_case(["нет", "да"])
        self.assertEqual(result["prediction_status"], "contradicted")
        self.assertEqual(fact["value"], "present")

    def test_retry(self):
        result, _, _ = self.run_case(["наверное", "да", "да"])
        self.assertEqual(result["status"], "PASS")

    def test_first_unknown_does_not_change_world(self):
        result, summary, fact = self.run_case(["не знаю", "может быть"])
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(summary["facts"], 0)
        self.assertIsNone(fact)

    def test_second_unknown_is_inconclusive(self):
        result, _, fact = self.run_case(["да", "не знаю", "может быть"])
        self.assertEqual(result["prediction_status"], "inconclusive")
        self.assertEqual(fact["value"], "present")


if __name__ == "__main__":
    unittest.main()
