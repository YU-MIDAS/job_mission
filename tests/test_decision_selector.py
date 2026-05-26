from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.config import RuntimeConfig
from mission_generation.decision_selector import (
    DecisionSelectorInputBuilder,
    DecisionSelectorValidator,
    MissionDecisionSelector,
)
from mission_generation.profile_loader import JobProfileLoader
from mission_generation.system_decision_builder import SystemDecisionBuilder


class RecordingSelectorRuntime:
    def __init__(self, output: dict[str, Any]) -> None:
        self.config = RuntimeConfig()
        self.output = output
        self.call_type: str | None = None
        self.schema_name: str | None = None

    def api_key_available(self) -> bool:
        return True

    def call_structured(
        self,
        *,
        call_type: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
        schema_name: str = "mission_output_v1_draft",
    ) -> dict[str, Any]:
        self.call_type = call_type
        self.schema_name = schema_name
        return {
            "schema_version": "llm_call_result.v1",
            "provider": "test",
            "status": "completed",
            "output_json": self.output,
            "usage": {"input_tokens": 2, "output_tokens": 1, "reasoning_tokens": 0, "total_tokens": 3},
            "errors": [],
        }


class DecisionSelectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = JobProfileLoader("data/api_raw").build("K000001080", save=False)
        cls.selector_input = DecisionSelectorInputBuilder().build(cls.profile, "normal")

    def _valid_result(self) -> dict[str, Any]:
        return {
            "selected_exec_job_id": "exec_003",
            "primary_task_type": "research_and_analysis",
            "selected_material_types": ["table", "chart"],
            "mission_design_type": "data_diagnosis",
            "matched_evidence": ["정보 처리", "논리적 분석"],
            "selection_reason": "대용량 데이터 처리·분석은 정보 처리와 논리적 분석 근거와 연결된다.",
            "confidence": "high",
        }

    def test_input_includes_selection_context(self) -> None:
        data = self.selector_input

        self.assertEqual(data["schema_version"], "decision_selector_input.v1")
        self.assertEqual(data["job_identity"]["job_cd"], "K000001080")
        self.assertGreaterEqual(len(data["exec_jobs"]), 3)
        self.assertIn("research_and_analysis", data["allowed_task_types"])
        self.assertIn("table", data["allowed_material_types"])
        self.assertIn("data_diagnosis", data["allowed_mission_design_types"])
        self.assertEqual(data["difficulty"]["material_count_range"], [2, 2])
        self.assertTrue(data["top_evidence"]["abilities"])

    def test_valid_selector_output_passes_validation(self) -> None:
        validation = DecisionSelectorValidator().validate(
            self.selector_input,
            self._valid_result(),
            job_profile=self.profile,
        )

        self.assertEqual(validation["status"], "passed")
        self.assertEqual(validation["errors"], [])

    def test_invalid_selector_output_fails_validation(self) -> None:
        invalid = self._valid_result()
        invalid.update(
            {
                "selected_exec_job_id": "exec_999",
                "primary_task_type": "not_allowed",
                "selected_material_types": ["table", "dashboard", "memo", "email"],
                "mission_design_type": "not_allowed",
                "matched_evidence": ["없는 근거"],
                "confidence": "certain",
            }
        )

        validation = DecisionSelectorValidator().validate(self.selector_input, invalid, job_profile=self.profile)
        codes = {error["code"] for error in validation["errors"]}

        self.assertEqual(validation["status"], "failed")
        self.assertIn("INVALID_EXEC_JOB_ID", codes)
        self.assertIn("INVALID_TASK_TYPE", codes)
        self.assertIn("INVALID_MATERIAL_TYPE", codes)
        self.assertIn("MATERIAL_COUNT_OUT_OF_RANGE", codes)
        self.assertIn("INVALID_MISSION_DESIGN_TYPE", codes)
        self.assertIn("INVALID_MATCHED_EVIDENCE", codes)
        self.assertIn("INVALID_CONFIDENCE", codes)

    def test_duplicate_selector_lists_fail_validation(self) -> None:
        duplicate = self._valid_result()
        duplicate["selected_material_types"] = ["table", "table"]
        duplicate["matched_evidence"] = [duplicate["matched_evidence"][0], duplicate["matched_evidence"][0]]

        validation = DecisionSelectorValidator().validate(self.selector_input, duplicate, job_profile=self.profile)
        codes = {error["code"] for error in validation["errors"]}

        self.assertEqual(validation["status"], "failed")
        self.assertIn("DUPLICATE_MATERIAL_TYPE", codes)
        self.assertIn("DUPLICATE_MATCHED_EVIDENCE", codes)

    def test_structured_output_schema_omits_unsupported_unique_items(self) -> None:
        schema = MissionDecisionSelector().structured_output_schema(self.selector_input)

        self.assertNotIn("uniqueItems", schema["properties"]["selected_material_types"])
        self.assertNotIn("uniqueItems", schema["properties"]["matched_evidence"])

    def test_selector_result_builds_system_decisions_shape(self) -> None:
        decisions = SystemDecisionBuilder().build_from_selector(self.profile, "normal", self._valid_result())

        self.assertEqual(decisions["schema_version"], "system_decisions.v1")
        self.assertEqual(decisions["selected_exec_job"]["exec_job_id"], "exec_003")
        self.assertEqual(decisions["primary_task_type"], "research_and_analysis")
        self.assertEqual(decisions["allowed_material_types"], ["table", "chart"])
        self.assertEqual(decisions["mission_design"]["mission_design_type"], "data_diagnosis")
        self.assertEqual(decisions["mission_design"]["selection_method"], "llm_decision_selector")
        self.assertEqual(decisions["decision_trace"][0]["step"], "llm_decision_selector")

    def test_selector_calls_runtime_with_selector_schema_name(self) -> None:
        runtime = RecordingSelectorRuntime(self._valid_result())
        result = MissionDecisionSelector(runtime=runtime).select(self.selector_input)  # type: ignore[arg-type]

        self.assertEqual(runtime.call_type, "decision_selection")
        self.assertEqual(runtime.schema_name, "decision_selector_v1")
        self.assertEqual(result["selector_result"]["selected_exec_job_id"], "exec_003")


if __name__ == "__main__":
    unittest.main()
