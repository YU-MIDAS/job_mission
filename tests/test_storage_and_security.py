# run 산출물 저장 구조와 비밀값 스캔 같은 안전장치를 검증한다.

from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_generation.config import RuntimeConfig, default_pilot_config
from mission_generation.storage import StorageAdapter
from mission_generation.utils import project_path, scan_text_for_secrets


class StorageAndSecurityTest(unittest.TestCase):
    def test_storage_outputs_parse_as_json(self) -> None:
        output_root = project_path("outputs", "_test_tmp", "storage_case")
        output_root.mkdir(parents=True, exist_ok=True)
        storage = StorageAdapter(output_root=output_root)
        storage.create_run(RuntimeConfig(), default_pilot_config())
        manifest = json.loads((storage.run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["llm_runtime"]["temperature_application"]["temperature_applied"])
        self.assertEqual(
            manifest["llm_runtime"]["temperature_application"]["temperature_omitted_reason"],
            "unsupported_by_model",
        )
        storage.write_run_json("jobs/KTEST/normal/run_status.json", {"schema_version": "x", "ok": True})
        self.assertEqual(storage.validate_json_outputs(), [])
        self.assertEqual(storage.security_scan(), [])

    def test_secret_scan_patterns(self) -> None:
        self.assertTrue(scan_text_for_secrets("Authorization: Bearer sk-proj-abcdefghijklmnopqrstuvwxyz"))
        self.assertTrue(scan_text_for_secrets("OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz"))
        self.assertEqual(scan_text_for_secrets("provider=openai model=gpt-5.4-mini"), [])


if __name__ == "__main__":
    unittest.main()
