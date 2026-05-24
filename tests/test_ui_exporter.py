from __future__ import annotations

import json
import re
import sys
import unittest
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.ui_exporter import DEFAULT_RUN_ID, MissionUIExporter
from mission_generation.utils import project_path, scan_text_for_secrets


class MissionUIExporterTest(unittest.TestCase):
    def _export_payload(self, run_id: str, output_name: str) -> tuple[str, dict]:
        pilot_run_dir = project_path("outputs", "pilot", "v1", "runs", run_id)
        if not pilot_run_dir.exists():
            self.skipTest(f"pilot run is not available: {pilot_run_dir}")
        output_dir = project_path("outputs", "_test_tmp", output_name)
        output_path = MissionUIExporter().export(
            run_id=run_id,
            pilot_run_dir=pilot_run_dir,
            ui_output_dir=output_dir,
        )
        html = output_path.read_text(encoding="utf-8")
        match = re.search(
            r'<script id="missionPayload" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        payload = json.loads((match.group(1) if match else "").replace("<\\/", "</"))
        return html, payload

    def test_exports_single_html_with_eight_embedded_missions(self) -> None:
        html, payload = self._export_payload(DEFAULT_RUN_ID, "ui_exporter")

        self.assertEqual(scan_text_for_secrets(html), [])
        self.assertEqual(payload["run_id"], DEFAULT_RUN_ID)
        self.assertEqual(payload["schema_version"], "mission_ui_payload.v1.1")
        self.assertEqual(len(payload["mission_slots"]), 8)
        self.assertEqual(sum(1 for slot in payload["mission_slots"] if slot["status"] == "saved"), 8)
        self.assertEqual(len(payload["missions"]), 8)
        first = payload["missions"][0]
        self.assertIn("mission_id", first)
        self.assertIn("job_cd", first)
        self.assertIn("difficulty", first)
        self.assertIn("materials", first)
        self.assertIn("tasks", first)
        self.assertIn("mission_slots", html)
        self.assertIn("task-answer", html)
        self.assertNotIn("answerBox", html)
        self.assertNotIn("localStorage", html)
        self.assertNotIn("sessionStorage", html)

    def test_partial_run_keeps_eight_slots_and_failed_reason(self) -> None:
        html, payload = self._export_payload("pilot_v1_20260524_133436", "ui_exporter_partial")

        self.assertEqual(len(payload["mission_slots"]), 8)
        self.assertEqual(len(payload["missions"]), 6)
        failed_slots = [slot for slot in payload["mission_slots"] if slot["status"] == "failed"]
        self.assertEqual(len(failed_slots), 2)
        self.assertTrue(any(slot["failure"]["reason_code"] == "OUTPUT_PARSE_FAILED" for slot in failed_slots))
        self.assertIn("OUTPUT_PARSE_FAILED", html)
        self.assertIn("response did not contain output text", html)
        self.assertEqual(scan_text_for_secrets(html), [])

    def test_missing_slot_without_saved_missions_exports_empty_state(self) -> None:
        root = project_path("outputs", "_test_tmp", "ui_exporter_missing", uuid4().hex)
        run_dir = root / "pilot_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "pilot_config.json").write_text(
            json.dumps(
                {
                    "schema_version": "pilot_generation_config.v1",
                    "source_root": "data/api_raw",
                    "jobs": [{"job_cd": "KTEST", "job_name": "테스트직무"}],
                    "difficulties": [{"code": "normal", "label": "보통"}],
                    "max_repair_attempts": 1,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
            newline="\n",
        )

        output_path = MissionUIExporter().export(
            run_id="missing_fixture",
            pilot_run_dir=run_dir,
            ui_output_dir=root / "ui",
        )
        html = output_path.read_text(encoding="utf-8")
        match = re.search(
            r'<script id="missionPayload" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        payload = json.loads((match.group(1) if match else "").replace("<\\/", "</"))

        self.assertEqual(len(payload["mission_slots"]), 1)
        self.assertEqual(payload["mission_slots"][0]["status"], "missing")
        self.assertEqual(payload["mission_slots"][0]["failure"]["reason_code"], "MISSION_OUTPUT_MISSING")
        self.assertEqual(payload["missions"], [])
        self.assertIn("No saved mission is available for this run.", html)


if __name__ == "__main__":
    unittest.main()
