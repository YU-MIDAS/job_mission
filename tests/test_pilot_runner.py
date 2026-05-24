from __future__ import annotations

import json
import re
import sys
import unittest
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.pilot_runner import PilotRunner
from mission_generation.ui_exporter import MissionUIExporter
from mission_generation.utils import project_path


class PilotRunnerParallelTest(unittest.TestCase):
    def _output_root(self) -> Path:
        root = project_path("outputs", "_test_tmp", "pilot_runner")
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"run_{uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_mock_parallel_run_writes_final_indexes_and_summary_metadata(self) -> None:
        output_root = self._output_root()
        summary = PilotRunner(force_mock=True, concurrency=2, output_root=output_root).run()
        run_dir = Path(summary["run_dir"])

        self.assertEqual(summary["total_targets"], 8)
        self.assertEqual(summary["concurrency"], 2)
        self.assertIn("started_at", summary)
        self.assertIn("finished_at", summary)
        self.assertIsInstance(summary["duration_seconds"], float)
        self.assertGreaterEqual(summary["duration_seconds"], 0.0)
        self.assertEqual(summary["post_run_checks"]["json_parse_failures"], [])
        self.assertEqual(summary["post_run_checks"]["secret_findings"], [])

        self.assertTrue((run_dir / "jobs" / "K000000997" / "normal" / "run_status.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000000997" / "normal" / "mission_seed.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000001080" / "normal" / "mission_seed.json").exists())
        self.assertFalse((run_dir / "jobs" / "K000000997" / "hard" / "mission_seed.json").exists())
        self.assertFalse((run_dir / "jobs" / "K000001179" / "normal" / "mission_seed.json").exists())
        for relative_path in [
            "artifact_index.json",
            "_failed/failure_index.json",
            "pilot_summary.json",
            "human_review/pilot_review.json",
        ]:
            json.loads((run_dir / relative_path).read_text(encoding="utf-8"))

    def test_parallel_run_records_one_target_failure_and_continues(self) -> None:
        output_root = self._output_root()
        runner = PilotRunner(force_mock=True, concurrency=2, output_root=output_root)
        original = runner._run_one_with_usage

        def fail_first_target(profile: dict, job: dict, difficulty: dict) -> dict:
            if job["job_cd"] == "K000000997" and difficulty["code"] == "normal":
                raise RuntimeError("forced target failure")
            return original(profile, job, difficulty)

        runner._run_one_with_usage = fail_first_target  # type: ignore[method-assign]
        summary = runner.run()
        run_dir = Path(summary["run_dir"])
        statuses = {item["status"] for item in summary["results"]}

        self.assertEqual(summary["total_targets"], 8)
        self.assertIn("runner_failed", statuses)
        self.assertGreaterEqual(summary["saved_count"], 1)
        self.assertEqual(summary["post_run_checks"]["json_parse_failures"], [])

        failed_status = json.loads(
            (run_dir / "jobs" / "K000000997" / "normal" / "run_status.json").read_text(encoding="utf-8")
        )
        self.assertEqual(failed_status["status"], "runner_failed")

    def test_target_filters_run_practice_profile_normal_missions_only(self) -> None:
        output_root = self._output_root()
        summary = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000000997", "K000001080"],
            target_difficulty_codes=["normal"],
        ).run()
        run_dir = Path(summary["run_dir"])

        self.assertEqual(summary["total_targets"], 2)
        self.assertEqual(summary["saved_count"], 2)
        self.assertEqual(summary["failed_count"], 0)

        pilot_config = json.loads((run_dir / "pilot_config.json").read_text(encoding="utf-8"))
        self.assertEqual([item["job_cd"] for item in pilot_config["jobs"]], ["K000000997", "K000001080"])
        self.assertEqual([item["code"] for item in pilot_config["difficulties"]], ["normal"])

        for job_cd in ["K000000997", "K000001080"]:
            self.assertTrue((run_dir / "jobs" / job_cd / "normal" / "mission_output.json").exists())
            self.assertTrue((run_dir / "jobs" / job_cd / "normal" / "job_practice_profile.json").exists())
            self.assertTrue((run_dir / "jobs" / job_cd / "normal" / "mission_seed.json").exists())
            self.assertFalse((run_dir / "jobs" / job_cd / "hard").exists())
        self.assertFalse((run_dir / "jobs" / "K000001179").exists())

        html_path = MissionUIExporter(output_root=output_root).export(
            run_id=summary["run_id"],
            pilot_run_dir=run_dir,
            ui_output_dir=output_root / "ui",
        )
        html = html_path.read_text(encoding="utf-8")
        match = re.search(r'<script id="missionPayload" type="application/json">(.*?)</script>', html, re.S)
        payload = json.loads((match.group(1) if match else "").replace("<\\/", "</"))
        self.assertEqual(len(payload["mission_slots"]), 2)
        self.assertEqual(len(payload["missions"]), 2)

    def test_target_filters_reject_unknown_codes(self) -> None:
        output_root = self._output_root()
        with self.assertRaisesRegex(ValueError, "Unknown job code"):
            PilotRunner(
                force_mock=True,
                output_root=output_root,
                target_job_codes=["K999999999"],
            ).run()
        with self.assertRaisesRegex(ValueError, "Unknown difficulty code"):
            PilotRunner(
                force_mock=True,
                output_root=output_root,
                target_difficulty_codes=["easy"],
            ).run()


if __name__ == "__main__":
    unittest.main()
