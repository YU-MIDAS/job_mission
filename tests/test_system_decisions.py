from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.draft_generator import LLMInputPackageBuilder, PromptBuilder
from mission_generation.mission_seed_builder import MissionSeedBuilder
from mission_generation.practice_profile_loader import PracticeProfileLoader
from mission_generation.profile_loader import JobProfileLoader
from mission_generation.schema_constraints_builder import SchemaConstraintsBuilder
from mission_generation.system_decision_builder import MISSION_DESIGN_TYPES, SystemDecisionBuilder


class SystemDecisionBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loader = JobProfileLoader("data/api_raw")
        cls.profile = cls.loader.build("K000000997", save=False)

    def test_product_planner_normal_decisions(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "normal")
        self.assertEqual(decisions["schema_version"], "system_decisions.v1")
        self.assertEqual(decisions["selected_exec_job"]["exec_job_id"], "exec_004")
        self.assertEqual(decisions["primary_task_type"], "research_and_analysis")
        self.assertEqual(decisions["allowed_material_types"], ["chart", "memo", "table"])
        self.assertEqual(decisions["difficulty"]["level"], "normal")
        self.assertIn("selection_reason", decisions["selected_exec_job"])
        self.assertEqual(decisions["mission_design"]["schema_version"], "mission_design.v1")
        self.assertEqual(decisions["mission_design"]["mission_design_type"], "market_feedback_prioritization")
        self.assertIn(decisions["mission_design"]["selection_method"], {"profile_signal_rule", "pilot_fallback", "general_fallback"})
        self.assertIn(decisions["mission_design"]["mission_design_type"], MISSION_DESIGN_TYPES)

    def test_product_planner_hard_decisions(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "hard")
        self.assertEqual(decisions["selected_exec_job"]["exec_job_id"], "exec_004")
        self.assertEqual(decisions["allowed_material_types"], ["email", "chart", "table", "schedule"])
        self.assertEqual(decisions["difficulty"]["material_count_range"], [3, 4])

    def test_pilot_mission_design_types(self) -> None:
        expected = {
            "K000000997": "market_feedback_prioritization",
            "K000001080": "data_diagnosis",
            "K000001179": "financial_research_judgment",
            "K000007519": "product_design_with_constraints",
        }
        for job_cd, design_type in expected.items():
            with self.subTest(job_cd=job_cd):
                profile = self.loader.build(job_cd, save=False)
                decisions = SystemDecisionBuilder().build(profile, "normal")
                self.assertEqual(decisions["mission_design"]["mission_design_type"], design_type)
                self.assertIn(decisions["mission_design"]["selection_method"], {"profile_signal_rule", "pilot_fallback", "general_fallback"})
                self.assertTrue(
                    any(item["step"] == "select_mission_design_type" for item in decisions["decision_trace"])
                )

    def test_llm_input_and_prompt_include_mission_design(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "normal")
        package = LLMInputPackageBuilder().build(self.profile, decisions, {})
        self.assertEqual(package["system_decisions"]["mission_design"], decisions["mission_design"])

        prompts = PromptBuilder().draft_prompts(package)
        self.assertIn("mission_design", prompts["user"])
        self.assertIn("mission_design_type", prompts["user"])
        self.assertIn("design_intent", prompts["user"])
        self.assertIn("Quality requirements", prompts["user"])
        self.assertIn("natural Korean", prompts["user"])
        self.assertIn("Make every material useful", prompts["user"])
        self.assertIn("For normal difficulty", prompts["user"])
        self.assertIn("For hard difficulty", prompts["user"])
        self.assertIn("trade-off judgment", prompts["user"])
        self.assertIn("Do not copy mission_design into mission_output", prompts["user"])
        self.assertIn("Return one complete valid JSON object", prompts["user"])
        self.assertIn("Do not truncate the JSON", prompts["user"])
        self.assertIn("Stability requirements", prompts["user"])
        self.assertIn("mission_fact_refs as key names only", prompts["user"])
        self.assertIn("rubric points sum exactly to 100", prompts["user"])
        self.assertIn("do not use material ids", prompts["user"])
        self.assertIn("Keep chart series count at 1 or 2", prompts["user"])

    def test_prompt_excludes_structured_output_schema_but_keeps_constraints(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "normal")
        constraints = SchemaConstraintsBuilder().build(evidence_names=["evidence_a"])
        package = LLMInputPackageBuilder().build(self.profile, decisions, constraints)

        prompts = PromptBuilder().draft_prompts(package)

        self.assertIn("structured_output_schema", package["schema_constraints"])
        self.assertNotIn("structured_output_schema", prompts["user"])
        self.assertIn("API structured output", prompts["user"])
        self.assertIn("schema_constraints", prompts["user"])
        self.assertIn("material_rules", prompts["user"])
        self.assertIn("allowed_evidence_names", prompts["user"])
        self.assertIn("evidence_a", prompts["user"])
        self.assertIn("mission_design", prompts["user"])

    def test_llm_input_and_prompt_include_practice_seed_when_available(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "normal")
        practice_profile = PracticeProfileLoader().load("K000000997")
        seed_builder = MissionSeedBuilder()
        seed = seed_builder.build(
            job_profile=self.profile,
            practice_profile=practice_profile,
            system_decisions=decisions,
        )
        self.assertIsNotNone(seed)
        excerpt = seed_builder.excerpt(practice_profile, seed)  # type: ignore[arg-type]
        package = LLMInputPackageBuilder().build(
            self.profile,
            decisions,
            {},
            job_practice_profile_excerpt=excerpt,
            mission_seed=seed,
        )

        self.assertEqual(package["mission_seed"], seed)
        self.assertEqual(package["job_practice_profile_excerpt"], excerpt)

        prompts = PromptBuilder().draft_prompts(package)
        self.assertIn("Practice survey requirements", prompts["user"])
        self.assertIn("Use mission_seed as the main design brief", prompts["user"])
        self.assertIn("mission_seed.material_blueprints", prompts["user"])
        self.assertIn("do not create a mission.guide field", prompts["user"])
        self.assertIn("do not create a direct quoted request sentence", prompts["user"])


if __name__ == "__main__":
    unittest.main()
