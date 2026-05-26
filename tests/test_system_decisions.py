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
        self.assertEqual(decisions["allowed_material_types"], ["chart", "memo"])
        self.assertEqual(decisions["difficulty"]["level"], "normal")
        self.assertEqual(decisions["difficulty"]["material_count_range"], [2, 2])
        self.assertEqual(decisions["difficulty"]["task_count_range"], [2, 2])
        self.assertEqual(decisions["difficulty"]["answer_length_hint"], "2-3 short sentences per task")
        self.assertIn("selection_reason", decisions["selected_exec_job"])
        self.assertEqual(decisions["mission_design"]["schema_version"], "mission_design.v1")
        self.assertEqual(decisions["mission_design"]["mission_design_type"], "market_feedback_prioritization")
        self.assertIn(decisions["mission_design"]["selection_method"], {"profile_signal_rule", "pilot_fallback", "general_fallback"})
        self.assertIn(decisions["mission_design"]["mission_design_type"], MISSION_DESIGN_TYPES)

    def test_product_planner_hard_decisions(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "hard")
        self.assertEqual(decisions["selected_exec_job"]["exec_job_id"], "exec_004")
        self.assertEqual(decisions["allowed_material_types"], ["email", "chart", "table"])
        self.assertEqual(decisions["difficulty"]["material_count_range"], [3, 3])
        self.assertEqual(decisions["difficulty"]["task_count_range"], [2, 2])
        self.assertEqual(decisions["difficulty"]["answer_length_hint"], "3-5 short sentences per task")
        self.assertFalse(decisions["difficulty"]["requires_tradeoff_judgment"])

    def test_product_planner_easy_decisions(self) -> None:
        decisions = SystemDecisionBuilder().build(self.profile, "easy")
        self.assertEqual(decisions["selected_exec_job"]["exec_job_id"], "exec_004")
        self.assertEqual(decisions["allowed_material_types"], ["memo"])
        self.assertEqual(decisions["difficulty"]["level"], "easy")
        self.assertEqual(decisions["difficulty"]["label"], "쉬움")
        self.assertEqual(decisions["difficulty"]["material_count_range"], [1, 1])
        self.assertEqual(decisions["difficulty"]["task_count_range"], [1, 1])
        self.assertEqual(decisions["difficulty"]["answer_length_hint"], "1-2 short sentences")
        self.assertFalse(decisions["difficulty"]["requires_cross_material_reasoning"])

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
        self.assertIn("For easy difficulty", prompts["user"])
        self.assertIn("For normal difficulty", prompts["user"])
        self.assertIn("For hard difficulty", prompts["user"])
        self.assertIn("Make the mission easier than a real workplace task", prompts["user"])
        self.assertIn("exactly 1 material and exactly 1 task", prompts["user"])
        self.assertIn("exactly 2 materials and exactly 2 tasks", prompts["user"])
        self.assertIn("exactly 3 materials and exactly 2 tasks", prompts["user"])
        self.assertIn("Hard means more materials, not expert-level reasoning", prompts["user"])
        self.assertIn("Do not ask for root-cause analysis", prompts["user"])
        self.assertIn("Each answer should be 2-3 short sentences", prompts["user"])
        self.assertIn("Each answer should be 3-5 short sentences", prompts["user"])
        self.assertIn("Every task must require only one learner action", prompts["user"])
        self.assertIn("short descriptive written response", prompts["user"])
        self.assertIn("letter-only", prompts["user"])
        self.assertIn("trade-off judgment", prompts["user"])
        self.assertIn("Do not copy mission_design into mission_output", prompts["user"])
        self.assertIn("Job-experience style requirements", prompts["user"])
        self.assertIn("docx/직무미션_ref.html", prompts["user"])
        self.assertIn("beginner, intern, assistant, or new team member", prompts["user"])
        self.assertIn("사전 전문지식", prompts["system"])
        self.assertIn("전문 자격 지식", prompts["system"])
        self.assertIn("아래 자료를 보고", prompts["user"])
        self.assertIn("without prior professional knowledge", prompts["user"])
        self.assertIn("용어 설명:", prompts["user"])
        self.assertIn("potentially confusing term", prompts["user"])
        self.assertIn("Return one complete valid JSON object", prompts["user"])
        self.assertIn("Do not truncate the JSON", prompts["user"])
        self.assertIn("Stability requirements", prompts["user"])
        self.assertIn("mission_fact_refs as key names only", prompts["user"])
        self.assertIn("rubric points sum exactly to 100", prompts["user"])
        self.assertIn("do not use material ids", prompts["user"])
        self.assertIn("log easy 2-3, normal 3-4, hard 3-4 entries", prompts["user"])
        self.assertIn("memo easy 1-2, normal 2-3, hard 2-3 items", prompts["user"])
        self.assertIn("schedule easy 1-2, normal 2-3, hard 2-3 items", prompts["user"])
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
