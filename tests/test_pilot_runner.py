# PilotRunner의 기본 생성 경로, 옵션 경로, 실패 처리, 진행 메시지를 검증한다.

from __future__ import annotations

import io
import json
import re
import sys
import unittest
from contextlib import redirect_stdout
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.pilot_runner import PilotRunner
from mission_generation.ui_exporter import MissionUIExporter
from mission_generation.utils import project_path


class StaticDecisionSelector:
    def select(self, selector_input: dict) -> dict:
        material_min = selector_input["difficulty"]["material_count_range"][0]
        evidence_name = selector_input["top_evidence"]["abilities"][0]["name"]
        selector_result = {
            "selected_exec_job_id": selector_input["exec_jobs"][0]["exec_job_id"],
            "primary_task_type": "research_and_analysis",
            "selected_material_types": selector_input["allowed_material_types"][:material_min],
            "mission_design_type": "general_research_analysis",
            "matched_evidence": [evidence_name],
            "selection_reason": "테스트 selector가 첫 번째 수행직무를 선택했다.",
            "confidence": "high",
        }
        return {
            "schema_version": "decision_selector_run.v1",
            "llm_call_result": {
                "schema_version": "llm_call_result.v1",
                "provider": "test",
                "status": "completed",
                "output_json": selector_result,
                "usage": {"input_tokens": 3, "output_tokens": 2, "reasoning_tokens": 0, "total_tokens": 5},
                "errors": [],
            },
            "selector_result": selector_result,
        }


class InvalidDecisionSelector:
    def select(self, selector_input: dict) -> dict:
        selector_result = {
            "selected_exec_job_id": "missing",
            "primary_task_type": "missing",
            "selected_material_types": ["missing"],
            "mission_design_type": "missing",
            "matched_evidence": ["missing"],
            "selection_reason": "invalid",
            "confidence": "missing",
        }
        return {
            "schema_version": "decision_selector_run.v1",
            "llm_call_result": {
                "schema_version": "llm_call_result.v1",
                "provider": "test",
                "status": "completed",
                "output_json": selector_result,
                "usage": {"input_tokens": 1, "output_tokens": 1, "reasoning_tokens": 0, "total_tokens": 2},
                "errors": [],
            },
            "selector_result": selector_result,
        }


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

        self.assertEqual(summary["total_targets"], 12)
        self.assertEqual(summary["concurrency"], 2)
        self.assertIn("started_at", summary)
        self.assertIn("finished_at", summary)
        self.assertIsInstance(summary["duration_seconds"], float)
        self.assertGreaterEqual(summary["duration_seconds"], 0.0)
        self.assertEqual(summary["post_run_checks"]["json_parse_failures"], [])
        self.assertEqual(summary["post_run_checks"]["secret_findings"], [])

        self.assertTrue((run_dir / "jobs" / "K000000997" / "normal" / "run_status.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000000997" / "easy" / "run_status.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000000997" / "normal" / "job_practice_sheet_background.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000001080" / "normal" / "job_practice_sheet_background.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000000997" / "easy" / "job_practice_sheet_background.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000000997" / "hard" / "job_practice_sheet_background.json").exists())
        self.assertTrue((run_dir / "jobs" / "K000001179" / "normal" / "job_practice_sheet_background.json").exists())
        self.assertFalse((run_dir / "jobs" / "K000000997" / "normal" / "mission_seed.json").exists())
        self.assertFalse((run_dir / "jobs" / "K000001080" / "normal" / "mission_seed.json").exists())
        self.assertFalse((run_dir / "jobs" / "K000000997" / "easy" / "mission_seed.json").exists())
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

        self.assertEqual(summary["total_targets"], 12)
        self.assertIn("runner_failed", statuses)
        self.assertGreaterEqual(summary["saved_count"], 1)
        self.assertEqual(summary["post_run_checks"]["json_parse_failures"], [])

        failed_status = json.loads(
            (run_dir / "jobs" / "K000000997" / "normal" / "run_status.json").read_text(encoding="utf-8")
        )
        self.assertEqual(failed_status["status"], "runner_failed")

    def test_target_filters_run_default_practice_sheet_background_missions_only(self) -> None:
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
            self.assertTrue((run_dir / "jobs" / job_cd / "normal" / "job_practice_sheet_background.json").exists())
            self.assertFalse((run_dir / "jobs" / job_cd / "normal" / "job_practice_profile.json").exists())
            self.assertFalse((run_dir / "jobs" / job_cd / "normal" / "mission_seed.json").exists())
            self.assertFalse((run_dir / "jobs" / job_cd / "easy").exists())
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

    def test_console_progress_messages_show_target_stages(self) -> None:
        output_root = self._output_root()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            summary = PilotRunner(
                force_mock=True,
                concurrency=1,
                output_root=output_root,
                target_job_codes=["K000001080"],
                target_difficulty_codes=["normal"],
                progress_enabled=True,
            ).run()
        progress_output = buffer.getvalue()

        self.assertEqual(summary["total_targets"], 1)
        self.assertIn("run started", progress_output)
        self.assertIn("[1/1] K000001080 normal - target started", progress_output)
        self.assertIn("[1/1] K000001080 normal - draft LLM started", progress_output)
        self.assertIn("[1/1] K000001080 normal - saved", progress_output)
        self.assertIn("run finished", progress_output)

    def test_practice_sheet_background_mode_omits_mission_seed(self) -> None:
        output_root = self._output_root()
        practice_sheet_root = output_root / "practice_sheets"
        practice_sheet_root.mkdir(parents=True, exist_ok=True)
        (practice_sheet_root / "K000001080.md").write_text("# 데이터분석가\n실무 조사 내용", encoding="utf-8")
        summary = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000001080"],
            target_difficulty_codes=["normal"],
            use_practice_sheet_background=True,
            practice_sheet_root=practice_sheet_root,
        ).run()
        run_dir = Path(summary["run_dir"])
        job_dir = run_dir / "jobs" / "K000001080" / "normal"
        llm_input = json.loads((job_dir / "llm_input_package.json").read_text(encoding="utf-8"))
        pilot_config = json.loads((run_dir / "pilot_config.json").read_text(encoding="utf-8"))
        run_status = json.loads((job_dir / "run_status.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["total_targets"], 1)
        self.assertEqual(summary["saved_count"], 1)
        self.assertTrue(pilot_config["use_practice_sheet_background"])
        self.assertIn("job_practice_sheet_background", llm_input)
        self.assertEqual(llm_input["job_practice_sheet_background"]["job_cd"], "K000001080")
        self.assertIn("데이터분석가", llm_input["job_practice_sheet_background"]["content_markdown"])
        self.assertNotIn("mission_seed", llm_input)
        self.assertNotIn("job_practice_profile_excerpt", llm_input)
        self.assertTrue((job_dir / "job_practice_sheet_background.json").exists())
        self.assertFalse((job_dir / "mission_seed.json").exists())
        self.assertEqual(run_status["artifacts"]["job_practice_sheet_background"], "job_practice_sheet_background.json")

    def test_legacy_mission_seed_mode_can_be_enabled(self) -> None:
        output_root = self._output_root()
        summary = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000001080"],
            target_difficulty_codes=["normal"],
            use_practice_sheet_background=False,
        ).run()
        run_dir = Path(summary["run_dir"])
        job_dir = run_dir / "jobs" / "K000001080" / "normal"
        llm_input = json.loads((job_dir / "llm_input_package.json").read_text(encoding="utf-8"))
        pilot_config = json.loads((run_dir / "pilot_config.json").read_text(encoding="utf-8"))

        self.assertFalse(pilot_config["use_practice_sheet_background"])
        self.assertIn("mission_seed", llm_input)
        self.assertIn("job_practice_profile_excerpt", llm_input)
        self.assertNotIn("job_practice_sheet_background", llm_input)
        self.assertTrue((job_dir / "job_practice_profile.json").exists())
        self.assertTrue((job_dir / "mission_seed.json").exists())
        self.assertFalse((job_dir / "job_practice_sheet_background.json").exists())

    def test_non_pilot_raw_api_job_uses_rule_fallback_without_auto_pilot_config(self) -> None:
        output_root = self._output_root()
        summary = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000000821"],
            target_difficulty_codes=["normal"],
        ).run()
        run_dir = Path(summary["run_dir"])

        self.assertEqual(summary["total_targets"], 1)
        self.assertEqual(summary["saved_count"], 1)
        self.assertEqual(summary["llm_usage"]["selector_fallback_count"], 1)
        self.assertFalse((output_root / "auto_pilot_configs" / "v1" / "K000000821.json").exists())
        self.assertFalse((run_dir / "jobs" / "K000000821" / "normal" / "auto_pilot_config.json").exists())
        system_decisions = json.loads(
            (run_dir / "jobs" / "K000000821" / "normal" / "system_decisions.json").read_text(encoding="utf-8")
        )
        self.assertEqual(system_decisions["decision_warnings"][0]["code"], "PILOT_CONFIG_MISSING")

    def test_no_llm_selector_uses_legacy_manual_config_without_auto_pilot_config(self) -> None:
        output_root = self._output_root()
        runner = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000000997"],
            target_difficulty_codes=["normal"],
            use_llm_decision_selector=False,
        )

        summary = runner.run()
        run_dir = Path(summary["run_dir"])
        system_decisions = json.loads(
            (run_dir / "jobs" / "K000000997" / "normal" / "system_decisions.json").read_text(encoding="utf-8")
        )

        self.assertEqual(summary["llm_usage"]["selector_call_count"], 0)
        self.assertEqual(summary["llm_usage"]["selector_fallback_count"], 0)
        self.assertFalse((run_dir / "jobs" / "K000000997" / "normal" / "auto_pilot_config.json").exists())
        self.assertEqual(system_decisions["selected_exec_job"]["exec_job_id"], "exec_004")

    def test_llm_selector_success_takes_precedence_over_manual_config(self) -> None:
        output_root = self._output_root()
        runner = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000000997"],
            target_difficulty_codes=["normal"],
        )
        runner.decision_selector = StaticDecisionSelector()  # type: ignore[assignment]

        summary = runner.run()
        run_dir = Path(summary["run_dir"])
        system_decisions = json.loads(
            (run_dir / "jobs" / "K000000997" / "normal" / "system_decisions.json").read_text(encoding="utf-8")
        )
        validation = json.loads(
            (run_dir / "jobs" / "K000000997" / "normal" / "decision_selector_validation.json").read_text(encoding="utf-8")
        )

        self.assertEqual(summary["llm_usage"]["selector_call_count"], 1)
        self.assertEqual(summary["llm_usage"]["selector_fallback_count"], 0)
        self.assertEqual(summary["llm_usage"]["selector_failed_count"], 0)
        self.assertEqual(validation["status"], "passed")
        self.assertEqual(system_decisions["selected_exec_job"]["exec_job_id"], "exec_001")
        self.assertEqual(system_decisions["mission_design"]["selection_method"], "llm_decision_selector")

    def test_llm_selector_validation_failure_fails_target_without_legacy_fallback(self) -> None:
        output_root = self._output_root()
        runner = PilotRunner(
            force_mock=True,
            concurrency=1,
            output_root=output_root,
            target_job_codes=["K000000997"],
            target_difficulty_codes=["normal"],
        )
        runner.decision_selector = InvalidDecisionSelector()  # type: ignore[assignment]

        summary = runner.run()
        run_dir = Path(summary["run_dir"])
        job_dir = run_dir / "jobs" / "K000000997" / "normal"
        validation = json.loads(
            (job_dir / "decision_selector_validation.json").read_text(encoding="utf-8")
        )
        run_status = json.loads(
            (job_dir / "run_status.json").read_text(encoding="utf-8")
        )

        self.assertEqual(summary["total_targets"], 1)
        self.assertEqual(summary["saved_count"], 0)
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["llm_usage"]["selector_call_count"], 1)
        self.assertEqual(summary["llm_usage"]["selector_fallback_count"], 0)
        self.assertEqual(summary["llm_usage"]["selector_failed_count"], 1)
        self.assertEqual(validation["status"], "failed")
        self.assertEqual(run_status["status"], "decision_failed")
        self.assertEqual(run_status["error"]["errors"][0]["code"], "INVALID_EXEC_JOB_ID")
        self.assertFalse((job_dir / "system_decisions.json").exists())
        self.assertFalse((job_dir / "mission_output.json").exists())
        self.assertFalse((job_dir / "auto_pilot_config.json").exists())

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
                target_difficulty_codes=["expert"],
            ).run()


if __name__ == "__main__":
    unittest.main()
