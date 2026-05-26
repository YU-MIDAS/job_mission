from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import OUTPUT_ROOT, RuntimeConfig, default_pilot_config
from .utils import iso_now, project_path, scan_path_for_secrets, seoul_now, write_json_atomic


class StorageAdapter:
    def __init__(self, output_root: str | Path = OUTPUT_ROOT) -> None:
        self.output_root = project_path(output_root)
        self.run_id: str | None = None
        self.run_dir: Path | None = None
        self.artifact_items: list[dict[str, Any]] = []
        self.failure_items: list[dict[str, Any]] = []

    def create_run(self, runtime_config: RuntimeConfig, pilot_config: dict[str, Any] | None = None) -> Path:
        pilot_config = pilot_config or default_pilot_config()
        self.run_id = self._make_run_id()
        self.run_dir = self.output_root / "pilot" / "v1" / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "run_manifest.v1",
            "run_id": self.run_id,
            "created_at": iso_now(),
            "timezone": "Asia/Seoul",
            "source_root": pilot_config["source_root"],
            "use_kmeans": False,
            "use_llm_decision_selector": bool(pilot_config.get("use_llm_decision_selector", True)),
            "use_practice_sheet_background": bool(pilot_config.get("use_practice_sheet_background", True)),
            "pipeline_version": "v1",
            "llm_runtime": runtime_config.as_manifest(),
            "jobs": pilot_config["jobs"],
            "difficulties": [item["code"] for item in pilot_config["difficulties"]],
            "max_repair_attempts": pilot_config["max_repair_attempts"],
        }
        self.write_run_json("run_manifest.json", manifest)
        self.write_run_json("pilot_config.json", pilot_config)
        self.write_run_json("_failed/failure_index.json", self._failure_index())
        self.write_human_review_templates([])
        return self.run_dir

    def save_canonical_profile(self, profile: dict[str, Any]) -> Path:
        job_cd = profile["job_identity"]["job_cd"]
        path = self.output_root / "profiles" / "v1" / f"{job_cd}.json"
        write_json_atomic(path, profile)
        return path

    def save_canonical_auto_pilot_config(self, auto_pilot_config: dict[str, Any]) -> Path:
        job_cd = auto_pilot_config["job_cd"]
        path = self.output_root / "auto_pilot_configs" / "v1" / f"{job_cd}.json"
        write_json_atomic(path, auto_pilot_config)
        return path

    def save_profile_snapshot(self, profile: dict[str, Any]) -> Path:
        self._require_run()
        job_cd = profile["job_identity"]["job_cd"]
        path = self.run_dir / "profiles" / f"{job_cd}.json"  # type: ignore[operator]
        write_json_atomic(path, profile)
        return path

    def save_job_artifact(self, job_cd: str, difficulty_code: str, file_name: str, data: Any) -> Path:
        self._require_run()
        path = self.run_dir / "jobs" / job_cd / difficulty_code / file_name  # type: ignore[operator]
        write_json_atomic(path, data)
        return path

    def save_run_status(
        self,
        *,
        job_cd: str,
        job_name: str,
        difficulty: dict[str, str],
        status: str,
        repair_count: int,
        reliability_score: float | None,
        warning_count: int,
        fail_count: int,
        artifacts: dict[str, str],
        error: dict[str, Any] | None = None,
    ) -> Path:
        data = {
            "schema_version": "mission_run_status.v1",
            "run_id": self.run_id,
            "job_cd": job_cd,
            "job_name": job_name,
            "difficulty": difficulty,
            "status": status,
            "repair_count": repair_count,
            "reliability_score": reliability_score,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "artifacts": artifacts,
            "error": error,
        }
        return self.save_job_artifact(job_cd, difficulty["code"], "run_status.json", data)

    def record_artifact_item(
        self,
        *,
        job_cd: str,
        difficulty_code: str,
        status: str,
        mission_output_path: str | None,
        validator_result_path: str | None,
        run_status_path: str,
        flush: bool = True,
    ) -> None:
        self.artifact_items.append(
            {
                "job_cd": job_cd,
                "difficulty_code": difficulty_code,
                "status": status,
                "mission_output_path": mission_output_path,
                "validator_result_path": validator_result_path,
                "run_status_path": run_status_path,
            }
        )
        if flush:
            self.write_run_json("artifact_index.json", self.artifact_index())

    def record_failure(
        self,
        *,
        job_cd: str,
        difficulty_code: str,
        status: str,
        reason_code: str,
        run_status_path: str,
        validator_result_path: str | None = None,
        flush: bool = True,
    ) -> None:
        self.failure_items.append(
            {
                "job_cd": job_cd,
                "difficulty_code": difficulty_code,
                "status": status,
                "reason_code": reason_code,
                "run_status_path": run_status_path,
                "validator_result_path": validator_result_path,
            }
        )
        if flush:
            self.write_run_json("_failed/failure_index.json", self._failure_index())

    def save_pilot_summary(self, summary: dict[str, Any]) -> Path:
        return self.write_run_json("pilot_summary.json", summary)

    def artifact_index(self) -> dict[str, Any]:
        return {"schema_version": "artifact_index.v1", "run_id": self.run_id, "items": self.artifact_items}

    def flush_indexes(self) -> None:
        self.write_run_json("artifact_index.json", self.artifact_index())
        self.write_run_json("_failed/failure_index.json", self._failure_index())

    def write_human_review_templates(self, results: list[dict[str, Any]]) -> None:
        self._require_run()
        review_items = []
        for result in results:
            if result.get("mission_id"):
                review_items.append(
                    {
                        "mission_id": result["mission_id"],
                        "job_cd": result["job_cd"],
                        "difficulty_code": result["difficulty_code"],
                        "review_status": "pending",
                        "checks": {
                            "scenario_natural": None,
                            "materials_useful": None,
                            "difficulty_appropriate": None,
                            "evidence_reasonable": None,
                            "submission_format_clear": None,
                        },
                        "notes": "",
                    }
                )
        review_json = {
            "schema_version": "pilot_review.v1",
            "run_id": self.run_id,
            "reviewer": "human",
            "reviewed_at": None,
            "items": review_items,
        }
        self.write_run_json("human_review/pilot_review.json", review_json)
        lines = [
            f"# Pilot Review {self.run_id}",
            "",
            "각 미션의 자연스러움, 자료 유용성, 난이도, evidence 연결, 제출 형식을 확인하세요.",
            "",
        ]
        for item in review_items:
            lines.append(f"- [{item['review_status']}] {item['mission_id']} ({item['job_cd']} / {item['difficulty_code']})")
        path = self.run_dir / "human_review" / "pilot_review.md"  # type: ignore[operator]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    def write_run_json(self, relative_path: str, data: Any) -> Path:
        self._require_run()
        path = self.run_dir / relative_path  # type: ignore[operator]
        write_json_atomic(path, data)
        return path

    def validate_json_outputs(self) -> list[str]:
        self._require_run()
        failures: list[str] = []
        for path in self.run_dir.rglob("*.json"):  # type: ignore[union-attr]
            try:
                import json

                json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                failures.append(path.relative_to(self.run_dir).as_posix())  # type: ignore[arg-type]
        return failures

    def security_scan(self) -> list[dict[str, str]]:
        self._require_run()
        return scan_path_for_secrets(self.run_dir)  # type: ignore[arg-type]

    def relative_to_run(self, path: Path | None) -> str | None:
        if path is None:
            return None
        self._require_run()
        return path.relative_to(self.run_dir).as_posix()  # type: ignore[arg-type]

    def _make_run_id(self) -> str:
        now = seoul_now()
        base = now.strftime("pilot_v1_%Y%m%d_%H%M%S")
        runs_root = self.output_root / "pilot" / "v1" / "runs"
        candidate = base
        suffix = 2
        while (runs_root / candidate).exists():
            candidate = f"{base}_{suffix:03d}"
            suffix += 1
        return candidate

    def _failure_index(self) -> dict[str, Any]:
        return {
            "schema_version": "failure_index.v1",
            "run_id": self.run_id,
            "failed_count": len(self.failure_items),
            "items": self.failure_items,
        }

    def _require_run(self) -> None:
        if self.run_id is None or self.run_dir is None:
            raise RuntimeError("create_run must be called first")
