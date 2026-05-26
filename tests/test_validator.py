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

    def test_task_instruction_style_is_not_a_validator_failure(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["mission"]["tasks"][0]["instruction"] = "자료를 확인하세요. 그리고 개선안을 제안하세요."
        result = MissionValidator().validate(
            job_profile=self.profile,
            system_decisions=self.decisions,
            mission_output_draft=draft,
            attempt=0,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])

    def test_code_only_answer_style_is_not_a_validator_failure(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["mission"]["tasks"][0]["instruction"] = "옵션 A/B/C 중 1개만 고르세요. 답은 \"옵션: A\"로만 작성하세요."
        result = MissionValidator().validate(
            job_profile=self.profile,
            system_decisions=self.decisions,
            mission_output_draft=draft,
            attempt=0,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["errors"], [])

    def test_reduced_material_item_bounds_are_enforced(self) -> None:
        validator = MissionValidator()
        max_counts = {
            "memo": {"easy": 2, "normal": 3, "hard": 3},
            "schedule": {"easy": 2, "normal": 3, "hard": 3},
            "checklist": {"easy": 2, "normal": 3, "hard": 3},
            "log": {"easy": 3, "normal": 4, "hard": 4},
        }

        for material_type, difficulty_counts in max_counts.items():
            for difficulty, max_count in difficulty_counts.items():
                with self.subTest(material_type=material_type, difficulty=difficulty):
                    errors: list[dict] = []
                    warnings: list[dict] = []
                    validator._validate_material_data(
                        {"type": material_type, "data": self._material_data(material_type, max_count)},
                        "mission.materials[0]",
                        difficulty,
                        errors,
                        warnings,
                    )
                    self.assertEqual(errors, [])

                    errors = []
                    warnings = []
                    validator._validate_material_data(
                        {"type": material_type, "data": self._material_data(material_type, max_count + 1)},
                        "mission.materials[0]",
                        difficulty,
                        errors,
                        warnings,
                    )
                    self.assertIn("MATERIAL_SIZE_TOO_LARGE", {item["code"] for item in errors})

    def _material_data(self, material_type: str, count: int) -> dict:
        if material_type == "memo":
            return {"items": [f"memo {index}" for index in range(count)]}
        if material_type == "schedule":
            return {"items": [{"period": f"{index}w", "task": f"task {index}"} for index in range(count)]}
        if material_type == "checklist":
            return {"items": [{"label": f"item {index}", "status": "unchecked"} for index in range(count)]}
        if material_type == "log":
            return {"entries": [{"time": f"{index}:00", "event": f"event {index}"} for index in range(count)]}
        raise AssertionError(f"Unsupported material type: {material_type}")


if __name__ == "__main__":
    unittest.main()
