from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.profile_loader import JobProfileLoader


class JobProfileLoaderTest(unittest.TestCase):
    def test_builds_pilot_profile_from_api_raw(self) -> None:
        profile = JobProfileLoader(save_output_root := "data/api_raw").build("K000000997", save=False)
        self.assertEqual(profile["schema_version"], "job_mission_profile.v1")
        self.assertEqual(profile["source_root"], save_output_root)
        self.assertEqual(profile["job_identity"]["job_cd"], "K000000997")
        self.assertEqual(profile["job_identity"]["job_smcl_nm"], "상품기획자")
        self.assertGreaterEqual(len(profile["work"]["exec_jobs"]), 4)
        self.assertEqual(profile["work"]["exec_jobs"][0]["exec_job_id"], "exec_001")
        self.assertEqual(len(profile["evidence"]["abilities"]), 5)
        self.assertEqual(len(profile["evidence"]["knowledge"]), 5)
        self.assertEqual(len(profile["evidence"]["work_environment"]), 5)
        self.assertEqual(len(profile["evidence"]["work_activities"]), 10)
        source_file = profile["work"]["exec_jobs"][0]["source_ref"]["file"]
        self.assertEqual(source_file, "K000000997/dtlGb_2.xml")
        self.assertNotIn("data/api_raw", source_file)
        self.assertEqual(profile["loader_errors"], [])


if __name__ == "__main__":
    unittest.main()
