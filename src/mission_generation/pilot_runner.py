from __future__ import annotations

import argparse
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .auto_pilot_config_generator import AutoPilotConfigGenerator
from .config import PILOT_JOB_CONFIGS, RuntimeConfig, default_pilot_config
from .decision_selector import DecisionSelectorInputBuilder, DecisionSelectorValidator, MissionDecisionSelector
from .draft_generator import LLMInputPackageBuilder, MissionDraftGenerator
from .final_assembler import FinalMissionAssembler
from .mission_seed_builder import MissionSeedBuilder
from .practice_profile_loader import PracticeProfileLoader
from .profile_loader import JobProfileLoader, ProfileLoadError
from .repair_manager import RepairManager, RepairPromptBuilder
from .schema_constraints_builder import SchemaConstraintsBuilder
from .storage import StorageAdapter
from .system_decision_builder import SystemDecisionBuilder
from .utils import iso_now, normalize_text
from .validator import MissionValidator


class PilotRunner:
    def __init__(
        self,
        *,
        source_root: str | Path = "data/api_raw",
        output_root: str | Path = "outputs",
        force_mock: bool = False,
        concurrency: int = 2,
        target_job_codes: list[str] | None = None,
        target_difficulty_codes: list[str] | None = None,
        use_llm_decision_selector: bool = True,
    ) -> None:
        self.source_root = Path(source_root)
        self.output_root = Path(output_root)
        self.force_mock = force_mock
        self.concurrency = max(1, int(concurrency))
        self.target_job_codes = list(target_job_codes) if target_job_codes is not None else None
        self.target_difficulty_codes = list(target_difficulty_codes) if target_difficulty_codes is not None else None
        self.use_llm_decision_selector = bool(use_llm_decision_selector)
        self.runtime_config = RuntimeConfig()
        self.profile_loader = JobProfileLoader(source_root=self.source_root, output_root=self.output_root / "profiles" / "v1")
        self.auto_config_generator = AutoPilotConfigGenerator()
        self.practice_profile_loader = PracticeProfileLoader()
        self.seed_builder = MissionSeedBuilder()
        self.decision_builder = SystemDecisionBuilder()
        self.selector_input_builder = DecisionSelectorInputBuilder()
        self.decision_selector = MissionDecisionSelector(force_mock=force_mock)
        self.selector_validator = DecisionSelectorValidator()
        self.constraints_builder = SchemaConstraintsBuilder()
        self.input_builder = LLMInputPackageBuilder()
        self.draft_generator = MissionDraftGenerator(allow_mock_without_key=True, force_mock=force_mock)
        self.repair_manager = RepairManager(allow_mock_without_key=True, force_mock=force_mock)
        self.validator = MissionValidator()
        self.assembler = FinalMissionAssembler()
        self.storage = StorageAdapter(output_root=self.output_root)

    def run(self) -> dict[str, Any]:
        started_at = iso_now()
        started_monotonic = time.monotonic()
        pilot_config = self._pilot_config()
        pilot_config["source_root"] = self.source_root.as_posix()
        pilot_config["concurrency"] = self.concurrency
        pilot_config["use_llm_decision_selector"] = self.use_llm_decision_selector
        run_dir = self.storage.create_run(self.runtime_config, pilot_config)
        results_by_order: dict[int, dict[str, Any]] = {}
        usage = self._empty_usage()
        targets: list[tuple[int, dict[str, Any], dict[str, str], dict[str, str]]] = []
        target_order = 0

        for job in pilot_config["jobs"]:
            job_cd = job["job_cd"]
            try:
                profile = self.profile_loader.build(job_cd, save=False)
                self.storage.save_canonical_profile(profile)
                self.storage.save_profile_snapshot(profile)
            except ProfileLoadError as exc:
                for difficulty in pilot_config["difficulties"]:
                    results_by_order[target_order] = self._save_failed_status(
                        job_cd=job_cd,
                        job_name=job["job_name"],
                        difficulty=difficulty,
                        status="profile_failed",
                        reason_code=exc.errors[0]["code"] if exc.errors else "PROFILE_FAILED",
                        error={"errors": exc.errors},
                        results=None,
                    )
                    target_order += 1
                continue

            for difficulty in pilot_config["difficulties"]:
                targets.append((target_order, profile, job, difficulty))
                target_order += 1

        if self.concurrency <= 1:
            for order, profile, job, difficulty in targets:
                try:
                    output = self._run_one_with_usage(profile, job, difficulty)
                except Exception as exc:
                    output = {
                        "result": self._save_failed_status(
                            job_cd=job["job_cd"],
                            job_name=job["job_name"],
                            difficulty=difficulty,
                            status="runner_failed",
                            reason_code="RUNNER_FAILED",
                            error={"message": str(exc)},
                            results=None,
                        ),
                        "usage": self._empty_usage(),
                    }
                results_by_order[order] = output["result"]
                self._merge_usage(usage, output["usage"])
        else:
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                future_targets = {
                    executor.submit(self._run_one_with_usage, profile, job, difficulty): (order, job, difficulty)
                    for order, profile, job, difficulty in targets
                }
                for future in as_completed(future_targets):
                    order, job, difficulty = future_targets[future]
                    try:
                        output = future.result()
                    except Exception as exc:
                        output = {
                            "result": self._save_failed_status(
                                job_cd=job["job_cd"],
                                job_name=job["job_name"],
                                difficulty=difficulty,
                                status="runner_failed",
                                reason_code="RUNNER_FAILED",
                                error={"message": str(exc)},
                                results=None,
                            ),
                            "usage": self._empty_usage(),
                        }
                    results_by_order[order] = output["result"]
                    self._merge_usage(usage, output["usage"])

        results = [results_by_order[idx] for idx in sorted(results_by_order)]
        self.storage.flush_indexes()
        finished_at = iso_now()
        duration_seconds = round(time.monotonic() - started_monotonic, 3)
        summary = self._summary(
            results,
            usage,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
        )
        self.storage.save_pilot_summary(summary)
        self.storage.write_human_review_templates(results)
        json_failures = self.storage.validate_json_outputs()
        secret_findings = self.storage.security_scan()
        summary["post_run_checks"] = {
            "json_parse_failures": json_failures,
            "secret_findings": secret_findings,
        }
        self.storage.save_pilot_summary(summary)
        summary["run_dir"] = run_dir.as_posix()
        return summary

    def _pilot_config(self) -> dict[str, Any]:
        base = default_pilot_config()
        pilot_config = {
            **base,
            "jobs": [dict(item) for item in base["jobs"]],
            "difficulties": [dict(item) for item in base["difficulties"]],
        }
        if self.target_job_codes is not None:
            requested = self._dedupe_codes(self.target_job_codes, "target_job_codes")
            known = {item["job_cd"]: item for item in pilot_config["jobs"]}
            jobs: list[dict[str, str]] = []
            unknown: list[str] = []
            for code in requested:
                if code in known:
                    jobs.append(dict(known[code]))
                    continue
                raw_api_job = self._job_from_raw_api(code)
                if raw_api_job is None:
                    unknown.append(code)
                else:
                    jobs.append(raw_api_job)
            if unknown:
                raise ValueError(
                    "Unknown job code(s): "
                    + ", ".join(unknown)
                    + ". Available job codes: "
                    + ", ".join(known)
                    + " or any job code under "
                    + self.source_root.as_posix()
                )
            pilot_config["jobs"] = jobs

        if self.target_difficulty_codes is not None:
            requested = self._dedupe_codes(self.target_difficulty_codes, "target_difficulty_codes")
            known = {item["code"]: item for item in pilot_config["difficulties"]}
            unknown = [code for code in requested if code not in known]
            if unknown:
                raise ValueError(
                    "Unknown difficulty code(s): "
                    + ", ".join(unknown)
                    + ". Available difficulty codes: "
                    + ", ".join(known)
                )
            pilot_config["difficulties"] = [dict(known[code]) for code in requested]

        return pilot_config

    def _dedupe_codes(self, values: list[str], label: str) -> list[str]:
        codes = [value.strip() for value in values if isinstance(value, str) and value.strip()]
        if not codes:
            raise ValueError(f"{label} must include at least one code.")
        return list(dict.fromkeys(codes))

    def _job_from_raw_api(self, job_cd: str) -> dict[str, str] | None:
        job_dir = self.source_root / job_cd
        if not job_dir.is_dir():
            return None
        job_name = job_cd
        path = job_dir / "dtlGb_2.xml"
        if path.exists():
            try:
                job_name = normalize_text(ET.parse(path).getroot().findtext("jobSmclNm")) or job_cd
            except ET.ParseError:
                job_name = job_cd
        return {"job_cd": job_cd, "job_name": job_name}

    def _run_one(
        self,
        profile: dict[str, Any],
        job: dict[str, str],
        difficulty: dict[str, str],
        usage: dict[str, int],
    ) -> dict[str, Any]:
        job_cd = job["job_cd"]
        difficulty_code = difficulty["code"]
        artifacts: dict[str, str] = {}
        repair_count = 0

        try:
            generated_from = (self.output_root / "profiles" / "v1" / f"{job_cd}.json").as_posix()
            auto_pilot_config = self.auto_config_generator.build(profile, generated_from=generated_from)
            self.storage.save_canonical_auto_pilot_config(auto_pilot_config)
            self.storage.save_job_artifact(job_cd, difficulty_code, "auto_pilot_config.json", auto_pilot_config)
            artifacts["auto_pilot_config"] = "auto_pilot_config.json"
            manual_config = PILOT_JOB_CONFIGS.get(job_cd)
            decision_config = manual_config if manual_config is not None else auto_pilot_config["config"]
            decisions = self._build_system_decisions(
                profile=profile,
                job_cd=job_cd,
                difficulty_code=difficulty_code,
                decision_config=decision_config,
                usage=usage,
                artifacts=artifacts,
            )
            evidence_names = self._evidence_names(profile)
            constraints = self.constraints_builder.build(evidence_names=evidence_names)
            practice_profile = self.practice_profile_loader.load(job_cd)
            mission_seed = self.seed_builder.build(
                job_profile=profile,
                practice_profile=practice_profile,
                system_decisions=decisions,
            )
            practice_excerpt = (
                self.seed_builder.excerpt(practice_profile, mission_seed)
                if practice_profile is not None and mission_seed is not None
                else None
            )
            llm_input = self.input_builder.build(
                profile,
                decisions,
                constraints,
                job_practice_profile_excerpt=practice_excerpt,
                mission_seed=mission_seed,
            )
            self.storage.save_job_artifact(job_cd, difficulty_code, "system_decisions.json", decisions)
            self.storage.save_job_artifact(job_cd, difficulty_code, "schema_constraints.json", constraints)
            self.storage.save_job_artifact(job_cd, difficulty_code, "llm_input_package.json", llm_input)
            artifacts.update(
                {
                    "system_decisions": "system_decisions.json",
                    "schema_constraints": "schema_constraints.json",
                    "llm_input_package": "llm_input_package.json",
                }
            )
            if practice_profile is not None and mission_seed is not None:
                self.storage.save_job_artifact(job_cd, difficulty_code, "job_practice_profile.json", practice_profile)
                self.storage.save_job_artifact(job_cd, difficulty_code, "mission_seed.json", mission_seed)
                artifacts.update(
                    {
                        "job_practice_profile": "job_practice_profile.json",
                        "mission_seed": "mission_seed.json",
                    }
                )
        except Exception as exc:
            return self._save_failed_status(
                job_cd=job_cd,
                job_name=job["job_name"],
                difficulty=difficulty,
                status="decision_failed",
                reason_code="DECISION_FAILED",
                error={"message": str(exc)},
                results=None,
            )

        generated = self.draft_generator.generate(llm_input)
        call_result = generated["llm_call_result"]
        draft = generated["mission_draft"]
        self._collect_usage(call_result, usage)
        if call_result["provider"] == "mock":
            usage["mock_draft_count"] += 1
        elif call_result["status"] == "completed":
            usage["draft_call_count"] += 1
        self.storage.save_job_artifact(job_cd, difficulty_code, "llm_call_result_attempt_0.json", call_result)
        artifacts["llm_call_result_attempt_0"] = "llm_call_result_attempt_0.json"
        if draft is None:
            return self._save_failed_status(
                job_cd=job_cd,
                job_name=job["job_name"],
                difficulty=difficulty,
                status="llm_failed",
                reason_code=(call_result.get("errors") or [{"code": "LLM_FAILED"}])[0]["code"],
                error={"errors": call_result.get("errors", [])},
                results=None,
            )

        self.storage.save_job_artifact(job_cd, difficulty_code, "mission_draft_attempt_0.json", draft)
        validation = self.validator.validate(
            job_profile=profile,
            system_decisions=decisions,
            mission_output_draft=draft,
            attempt=0,
        )
        validator_path = self.storage.save_job_artifact(job_cd, difficulty_code, "validator_result_attempt_0.json", validation)
        artifacts.update(
            {
                "mission_draft_attempt_0": "mission_draft_attempt_0.json",
                "validator_result_attempt_0": "validator_result_attempt_0.json",
            }
        )

        if validation["status"] == "repair_required":
            repair_request = RepairPromptBuilder().build(decisions, draft, validation, self._evidence_names(profile))
            self.storage.save_job_artifact(job_cd, difficulty_code, "repair_request_attempt_1.json", repair_request)
            repaired = self.repair_manager.repair(
                repair_request=repair_request,
                json_schema=constraints["structured_output_schema"],
            )
            repair_call = repaired["llm_call_result"]
            draft = repaired["mission_draft"]
            repair_count = 1
            self._collect_usage(repair_call, usage)
            if repair_call["provider"] == "mock":
                usage["mock_repair_count"] += 1
            elif repair_call["status"] == "completed":
                usage["repair_call_count"] += 1
            self.storage.save_job_artifact(job_cd, difficulty_code, "llm_call_result_attempt_1.json", repair_call)
            self.storage.save_job_artifact(job_cd, difficulty_code, "mission_draft_attempt_1.json", draft)
            validation = self.validator.validate(
                job_profile=profile,
                system_decisions=decisions,
                mission_output_draft=draft,
                attempt=1,
            )
            validator_path = self.storage.save_job_artifact(job_cd, difficulty_code, "validator_result_attempt_1.json", validation)
            artifacts.update(
                {
                    "repair_request_attempt_1": "repair_request_attempt_1.json",
                    "llm_call_result_attempt_1": "llm_call_result_attempt_1.json",
                    "mission_draft_attempt_1": "mission_draft_attempt_1.json",
                    "validator_result_attempt_1": "validator_result_attempt_1.json",
                }
            )

        if validation["status"] == "pass":
            final_output = self.assembler.assemble(
                mission_output_draft=draft,
                validator_result=validation,
                job_cd=job_cd,
                difficulty_code=difficulty_code,
                repair_count=repair_count,
            )
            mission_path = self.storage.save_job_artifact(job_cd, difficulty_code, "mission_output.json", final_output)
            artifacts["mission_output"] = "mission_output.json"
            status_path = self.storage.save_run_status(
                job_cd=job_cd,
                job_name=profile["job_identity"].get("job_smcl_nm") or job["job_name"],
                difficulty=difficulty,
                status="saved",
                repair_count=repair_count,
                reliability_score=final_output["reliability"]["score"],
                warning_count=final_output["reliability"]["warning_count"],
                fail_count=final_output["reliability"]["fail_count"],
                artifacts=artifacts,
                error=None,
            )
            result = {
                "job_cd": job_cd,
                "job_name": profile["job_identity"].get("job_smcl_nm") or job["job_name"],
                "difficulty_code": difficulty_code,
                "status": "saved",
                "mission_id": final_output["mission_id"],
                "reliability_score": final_output["reliability"]["score"],
                "warning_count": final_output["reliability"]["warning_count"],
                "repair_count": repair_count,
                "mission_output_path": self.storage.relative_to_run(mission_path),
            }
            self.storage.record_artifact_item(
                job_cd=job_cd,
                difficulty_code=difficulty_code,
                status="saved",
                mission_output_path=self.storage.relative_to_run(mission_path),
                validator_result_path=self.storage.relative_to_run(validator_path),
                run_status_path=self.storage.relative_to_run(status_path) or "",
                flush=False,
            )
            return result

        status = "discarded" if validation["status"] == "discard" else "repair_failed"
        status_path = self.storage.save_run_status(
            job_cd=job_cd,
            job_name=profile["job_identity"].get("job_smcl_nm") or job["job_name"],
            difficulty=difficulty,
            status=status,
            repair_count=repair_count,
            reliability_score=validation["reliability"]["score"],
            warning_count=validation["reliability"]["warning_count"],
            fail_count=validation["reliability"]["fail_count"],
            artifacts=artifacts,
            error={"errors": validation["errors"], "warnings": validation["warnings"]},
        )
        self.storage.record_artifact_item(
            job_cd=job_cd,
            difficulty_code=difficulty_code,
            status=status,
            mission_output_path=None,
            validator_result_path=self.storage.relative_to_run(validator_path),
            run_status_path=self.storage.relative_to_run(status_path) or "",
            flush=False,
        )
        self.storage.record_failure(
            job_cd=job_cd,
            difficulty_code=difficulty_code,
            status=status,
            reason_code=(validation["errors"] or [{"code": "VALIDATOR_FAILED"}])[0]["code"],
            run_status_path=self.storage.relative_to_run(status_path) or "",
            validator_result_path=self.storage.relative_to_run(validator_path),
            flush=False,
        )
        return {
            "job_cd": job_cd,
            "job_name": profile["job_identity"].get("job_smcl_nm") or job["job_name"],
            "difficulty_code": difficulty_code,
            "status": status,
            "mission_id": None,
            "reliability_score": validation["reliability"]["score"],
            "warning_count": validation["reliability"]["warning_count"],
            "repair_count": repair_count,
            "mission_output_path": None,
        }

    def _save_failed_status(
        self,
        *,
        job_cd: str,
        job_name: str,
        difficulty: dict[str, str],
        status: str,
        reason_code: str,
        error: dict[str, Any],
        results: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        status_path = self.storage.save_run_status(
            job_cd=job_cd,
            job_name=job_name,
            difficulty=difficulty,
            status=status,
            repair_count=0,
            reliability_score=None,
            warning_count=0,
            fail_count=1,
            artifacts={},
            error=error,
        )
        self.storage.record_artifact_item(
            job_cd=job_cd,
            difficulty_code=difficulty["code"],
            status=status,
            mission_output_path=None,
            validator_result_path=None,
            run_status_path=self.storage.relative_to_run(status_path) or "",
            flush=False,
        )
        self.storage.record_failure(
            job_cd=job_cd,
            difficulty_code=difficulty["code"],
            status=status,
            reason_code=reason_code,
            run_status_path=self.storage.relative_to_run(status_path) or "",
            flush=False,
        )
        result = {
            "job_cd": job_cd,
            "job_name": job_name,
            "difficulty_code": difficulty["code"],
            "status": status,
            "mission_id": None,
            "reliability_score": None,
            "warning_count": 0,
            "repair_count": 0,
            "mission_output_path": None,
        }
        if results is not None:
            results.append(result)
        return result

    def _run_one_with_usage(
        self,
        profile: dict[str, Any],
        job: dict[str, str],
        difficulty: dict[str, str],
    ) -> dict[str, Any]:
        usage = self._empty_usage()
        result = self._run_one(profile, job, difficulty, usage)
        return {"result": result, "usage": usage}

    def _build_system_decisions(
        self,
        *,
        profile: dict[str, Any],
        job_cd: str,
        difficulty_code: str,
        decision_config: dict[str, Any],
        usage: dict[str, int],
        artifacts: dict[str, str],
    ) -> dict[str, Any]:
        if not self.use_llm_decision_selector:
            return self.decision_builder.build(profile, difficulty_code, decision_config)

        selector_input = self.selector_input_builder.build(profile, difficulty_code)
        self.storage.save_job_artifact(job_cd, difficulty_code, "decision_selector_input.json", selector_input)
        artifacts["decision_selector_input"] = "decision_selector_input.json"

        selector_run = self.decision_selector.select(selector_input)
        call_result = selector_run["llm_call_result"]
        selector_result = selector_run.get("selector_result")
        self._collect_usage(call_result, usage)
        if call_result.get("status") == "completed" and call_result.get("provider") != "local":
            usage["selector_call_count"] += 1
        self.storage.save_job_artifact(job_cd, difficulty_code, "decision_selector_call_result.json", call_result)
        self.storage.save_job_artifact(job_cd, difficulty_code, "decision_selector_result.json", selector_result)
        artifacts.update(
            {
                "decision_selector_call_result": "decision_selector_call_result.json",
                "decision_selector_result": "decision_selector_result.json",
            }
        )

        validation = self.selector_validator.validate(selector_input, selector_result, job_profile=profile)
        self.storage.save_job_artifact(job_cd, difficulty_code, "decision_selector_validation.json", validation)
        artifacts["decision_selector_validation"] = "decision_selector_validation.json"
        if validation["status"] == "passed":
            return self.decision_builder.build_from_selector(profile, difficulty_code, selector_result)

        usage["selector_fallback_count"] += 1
        return self.decision_builder.build(profile, difficulty_code, decision_config)

    def _empty_usage(self) -> dict[str, int]:
        return {
            "selector_call_count": 0,
            "selector_fallback_count": 0,
            "draft_call_count": 0,
            "repair_call_count": 0,
            "mock_draft_count": 0,
            "mock_repair_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }

    def _merge_usage(self, total: dict[str, int], delta: dict[str, int]) -> None:
        for key in total:
            total[key] += int(delta.get(key) or 0)

    def _collect_usage(self, call_result: dict[str, Any], usage: dict[str, int]) -> None:
        call_usage = call_result.get("usage") or {}
        for key in ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens"):
            usage[key] += int(call_usage.get(key) or 0)

    def _evidence_names(self, profile: dict[str, Any]) -> list[str]:
        names: list[str] = []
        for group in profile.get("evidence", {}).values():
            for item in group:
                name = item.get("name") if isinstance(item, dict) else None
                if isinstance(name, str) and name and name not in names:
                    names.append(name)
        return names

    def _summary(
        self,
        results: list[dict[str, Any]],
        usage: dict[str, int],
        *,
        started_at: str,
        finished_at: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        saved = [item for item in results if item["status"] == "saved"]
        failed = [item for item in results if item["status"] != "saved"]
        scores = [item["reliability_score"] for item in saved if item.get("reliability_score") is not None]
        return {
            "schema_version": "pilot_summary.v1",
            "run_id": self.storage.run_id,
            "created_at": iso_now(),
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration_seconds,
            "concurrency": self.concurrency,
            "total_targets": len(results),
            "saved_count": len(saved),
            "failed_count": len(failed),
            "repair_used_count": sum(1 for item in results if item["repair_count"] > 0),
            "average_reliability_score": round(sum(scores) / len(scores), 2) if scores else None,
            "llm_usage": usage,
            "openai_api_called": usage["selector_call_count"] + usage["draft_call_count"] + usage["repair_call_count"] > 0,
            "results": results,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mission generation v1 pilot.")
    parser.add_argument("--source-root", default="data/api_raw")
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--mock", action="store_true", help="Use local mock generation even when API key is absent.")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of job/difficulty targets to run in parallel.")
    parser.add_argument("--jobs", type=_parse_codes, default=None, help="Comma-separated job codes to run, e.g. K000000997,K000001080.")
    parser.add_argument("--difficulties", type=_parse_codes, default=None, help="Comma-separated difficulty codes to run, e.g. normal.")
    parser.add_argument("--no-llm-selector", action="store_true", help="Disable the LLM decision selector and use legacy system decision rules.")
    args = parser.parse_args()
    runner = PilotRunner(
        source_root=args.source_root,
        output_root=args.output_root,
        force_mock=args.mock,
        concurrency=args.concurrency,
        target_job_codes=args.jobs,
        target_difficulty_codes=args.difficulties,
        use_llm_decision_selector=not args.no_llm_selector,
    )
    try:
        summary = runner.run()
    except ValueError as exc:
        parser.error(str(exc))
    print(summary["run_dir"])
    print(f"saved={summary['saved_count']} failed={summary['failed_count']} openai_api_called={summary['openai_api_called']}")


def _parse_codes(value: str) -> list[str]:
    codes = [part.strip() for part in value.split(",") if part.strip()]
    if not codes:
        raise argparse.ArgumentTypeError("must include at least one comma-separated code")
    return codes


if __name__ == "__main__":
    main()
