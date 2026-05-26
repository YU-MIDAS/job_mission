from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.config import PILOT_JOB_CONFIGS
from mission_generation.mission_seed_builder import MissionSeedBuilder
from mission_generation.practice_profile_loader import PracticeProfileLoader
from mission_generation.practice_sheet_background_loader import PracticeSheetBackgroundLoader
from mission_generation.profile_loader import JobProfileLoader
from mission_generation.system_decision_builder import SystemDecisionBuilder
from mission_generation.utils import project_path


class PracticeProfileIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.practice_loader = PracticeProfileLoader()
        cls.profile_loader = JobProfileLoader("data/api_raw")
        cls.decision_builder = SystemDecisionBuilder()
        cls.seed_builder = MissionSeedBuilder()

    def test_practice_profile_loads_and_missing_job_returns_none(self) -> None:
        profile = self.practice_loader.load("K000001080")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["schema_version"], "job_practice_profile.v1")
        self.assertEqual(profile["job_identity"]["job_cd"], "K000001080")
        self.assertEqual(profile["request_examples"], [])

        self.assertIsNone(self.practice_loader.load("K000001179"))

    def test_data_analyst_normal_seed(self) -> None:
        seed = self._seed("K000001080", "normal")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["schema_version"], "mission_seed.normal.v1")
        self.assertEqual(seed["difficulty"], "normal")
        self.assertEqual(seed["scenario_basis"]["request_sentence"], "")
        self.assertGreaterEqual(len(seed["material_blueprints"]), 2)
        self.assertLessEqual(len(seed["material_blueprints"]), 3)
        self.assertEqual(seed["material_blueprints"][0]["material_role"], "primary")
        self.assertTrue(seed["task_plan"])
        self.assertTrue(seed["guide_plan"])
        self.assertTrue(seed["evaluation_basis"])

    def test_product_planner_normal_seed(self) -> None:
        seed = self._seed("K000000997", "normal")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["job_cd"], "K000000997")
        self.assertEqual(seed["scenario_basis"]["learner_role"], "신입 상품기획자")
        self.assertGreaterEqual(len(seed["material_blueprints"]), 2)

        practice_profile = self.practice_loader.load("K000000997")
        excerpt = self.seed_builder.excerpt(practice_profile, seed)  # type: ignore[arg-type]
        self.assertEqual(excerpt["job_identity"]["job_cd"], "K000000997")
        self.assertTrue(excerpt["selected_decision_situation"])
        self.assertTrue(excerpt["selected_practice_materials"])
        self.assertTrue(excerpt["selected_response_flow"])

    def test_hard_and_missing_practice_profile_do_not_create_seed(self) -> None:
        self.assertIsNone(self._seed("K000001080", "hard"))
        self.assertIsNone(self._seed("K000001179", "normal"))

    def test_practice_sheet_background_loader_reads_markdown_by_job_code(self) -> None:
        root = project_path("outputs", "_test_tmp", "practice_sheet_loader", uuid4().hex)
        root.mkdir(parents=True, exist_ok=True)
        (root / "K000001080.md").write_text("# 데이터분석가\n실무 조사 내용", encoding="utf-8")
        background = PracticeSheetBackgroundLoader(root=root).load("K000001080")

        self.assertIsNotNone(background)
        self.assertEqual(background["schema_version"], "job_practice_sheet_background.v1")  # type: ignore[index]
        self.assertEqual(background["job_cd"], "K000001080")  # type: ignore[index]
        self.assertTrue(background["source_path"].endswith("K000001080.md"))  # type: ignore[index]
        self.assertEqual(background["usage"], "background_only")  # type: ignore[index]
        self.assertIn("데이터분석가", background["content_markdown"])  # type: ignore[index]

        self.assertIsNone(PracticeSheetBackgroundLoader(root=root).load("K999999999"))

    def _seed(self, job_cd: str, difficulty: str) -> dict | None:
        profile = self.profile_loader.build(job_cd, save=False)
        decisions = self.decision_builder.build(profile, difficulty, PILOT_JOB_CONFIGS.get(job_cd, {}))
        practice_profile = self.practice_loader.load(job_cd)
        return self.seed_builder.build(
            job_profile=profile,
            practice_profile=practice_profile,
            system_decisions=decisions,
        )


if __name__ == "__main__":
    unittest.main()
