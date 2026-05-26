from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.draft_generator import LLMInputPackageBuilder, MockMissionDraftBuilder
from mission_generation.profile_loader import JobProfileLoader
from mission_generation.schema_constraints_builder import SchemaConstraintsBuilder
from mission_generation.system_decision_builder import SystemDecisionBuilder
from mission_generation.validator import MissionValidator


class MissionValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = JobProfileLoader("data/api_raw").build("K000000997", save=False)
        cls.decisions = SystemDecisionBuilder().build(cls.profile, "normal")
        constraints = SchemaConstraintsBuilder().build()
        cls.package = LLMInputPackageBuilder().build(cls.profile, cls.decisions, constraints)
        cls.draft = MockMissionDraftBuilder().build(cls.package)

    def test_mock_draft_passes_core_validator(self) -> None:
        result = MissionValidator().validate(
            job_profile=self.profile,
            system_decisions=self.decisions,
            mission_output_draft=self.draft,
            attempt=0,
        )
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["reliability"]["score"], 0.75)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["final_evidence_chain"]["created_by"], "validator.v1")

    def test_reliability_score_from_llm_is_fail(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["reliability"] = {"status": "pending_validation", "score": 0.9}
        result = MissionValidator().validate(
            job_profile=self.profile,
            system_decisions=self.decisions,
            mission_output_draft=draft,
            attempt=0,
        )
        self.assertEqual(result["status"], "repair_required")
        self.assertIn("LLM_RELIABILITY_SCORE_CREATED", {item["code"] for item in result["errors"]})

    def test_disallowed_material_type_fails(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["mission"]["materials"][0]["type"] = "image"
        result = MissionValidator().validate(
            job_profile=self.profile,
            system_decisions=self.decisions,
            mission_output_draft=draft,
            attempt=0,
        )
        codes = {item["code"] for item in result["errors"]}
        self.assertIn("EXCLUDED_MATERIAL_USED", codes)

    def test_task_with_multiple_actions_requires_repair(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["mission"]["tasks"][0]["instruction"] = "자료를 확인하세요. 그리고 개선안을 제안하세요."
        result = MissionValidator().validate(
            job_profile=self.profile,
            system_decisions=self.decisions,
            mission_output_draft=draft,
            attempt=0,
        )

        self.assertEqual(result["status"], "repair_required")
        self.assertIn("TASK_MULTIPLE_ACTIONS", {item["code"] for item in result["errors"]})


if __name__ == "__main__":
    unittest.main()
