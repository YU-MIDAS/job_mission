from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.auto_pilot_config_generator import AutoPilotConfigGenerator
from mission_generation.config import EXCLUDED_MATERIAL_TYPES, MATERIAL_TYPES, PILOT_JOB_CONFIGS
from mission_generation.profile_loader import JobProfileLoader


class AutoPilotConfigGeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loader = JobProfileLoader("data/api_raw")
        cls.generator = AutoPilotConfigGenerator()

    def test_builds_schema_compatible_config(self) -> None:
        profile = self.loader.build("K000001080", save=False)
        auto_config = self.generator.build(profile, generated_from="outputs/profiles/v1/K000001080.json")
        config = auto_config["config"]

        self.assertEqual(auto_config["schema_version"], "auto_pilot_config.v1")
        self.assertEqual(auto_config["job_cd"], "K000001080")
        self.assertEqual(auto_config["source"]["profile_schema_version"], "job_mission_profile.v1")
        self.assertEqual(auto_config["source"]["generated_from"], "outputs/profiles/v1/K000001080.json")
        self.assertIn("preferred_exec_job_id", config)
        self.assertIn("preferred_exec_job_keywords", config)
        self.assertIn("preferred_primary_task_type", config)
        self.assertIn("materials", config)
        self.assertIsInstance(auto_config["decision_trace"], list)
        self.assertIn(auto_config["confidence"]["level"], {"high", "medium", "low"})

    def test_output_is_deterministic(self) -> None:
        profile = self.loader.build("K000000997", save=False)
        first = self.generator.build(copy.deepcopy(profile))
        second = self.generator.build(copy.deepcopy(profile))

        self.assertEqual(first, second)

    def test_materials_stay_within_allowed_types(self) -> None:
        profile = self.loader.build("K000007519", save=False)
        auto_config = self.generator.build(profile)
        materials = auto_config["config"]["materials"]

        for difficulty in ("normal", "hard"):
            for material_type in materials[difficulty]:
                self.assertIn(material_type, MATERIAL_TYPES)
                self.assertNotIn(material_type, EXCLUDED_MATERIAL_TYPES)

    def test_malformed_profile_requires_review(self) -> None:
        profile = {
            "schema_version": "job_mission_profile.v1",
            "job_identity": {"job_cd": "KTEST", "job_smcl_nm": "테스트직무"},
            "work": {"exec_jobs": []},
            "evidence": {"work_activities": [], "knowledge": [], "abilities": []},
        }
        auto_config = self.generator.build(profile)
        warning_codes = {item["code"] for item in auto_config["decision_warnings"]}

        self.assertEqual(auto_config["config"]["preferred_exec_job_id"], "")
        self.assertTrue(auto_config["confidence"]["review_required"])
        self.assertIn("EXEC_JOBS_MISSING", warning_codes)
        self.assertIn("MATERIAL_CANDIDATE_BELOW_TARGET", warning_codes)

    def test_trimmed_material_candidates_are_trace_not_warning(self) -> None:
        profile = self.loader.build("K000001080", save=False)
        auto_config = self.generator.build(profile)
        warning_codes = {item["code"] for item in auto_config["decision_warnings"]}
        hard_trace = next(item for item in auto_config["decision_trace"] if item["step"] == "select_materials_hard")

        self.assertNotIn("MATERIAL_CANDIDATE_TRIMMED", warning_codes)
        self.assertIn("trimmed_candidates", hard_trace)

    def test_pilot_golden_comparison(self) -> None:
        for job_cd, expected in PILOT_JOB_CONFIGS.items():
            with self.subTest(job_cd=job_cd):
                profile = self.loader.build(job_cd, save=False)
                auto_config = self.generator.build(profile)
                config = auto_config["config"]

                self.assertEqual(config["preferred_exec_job_id"], expected["preferred_exec_job_id"])
                self.assertEqual(config["preferred_primary_task_type"], expected["preferred_primary_task_type"])
                self.assertGreaterEqual(
                    len(set(config["materials"]["normal"]) & set(expected["materials"]["normal"])),
                    2,
                )
                self.assertGreaterEqual(
                    len(set(config["materials"]["hard"]) & set(expected["materials"]["hard"])),
                    3,
                )


if __name__ == "__main__":
    unittest.main()
