from __future__ import annotations

import copy
from typing import Any


class FinalMissionAssembler:
    def assemble(
        self,
        *,
        mission_output_draft: dict[str, Any],
        validator_result: dict[str, Any],
        job_cd: str,
        difficulty_code: str,
        repair_count: int,
        sequence: int = 1,
    ) -> dict[str, Any]:
        if not validator_result.get("passed"):
            raise ValueError("validator_result must pass before final assembly")
        final_output = copy.deepcopy(mission_output_draft)
        final_output["schema_version"] = "mission_output.v1"
        final_output["mission_id"] = f"mission_{job_cd}_{difficulty_code}_{sequence:03d}"
        final_output.pop("evidence_chain_draft", None)
        final_output.pop("evidence_chain", None)
        final_output["evidence_chain"] = copy.deepcopy(validator_result["final_evidence_chain"])
        reliability = validator_result["reliability"]
        final_output["reliability"] = {
            "score": reliability["score"],
            "raw_score": reliability["raw_score"],
            "passed": True,
            "calculated_by": "validator.v1",
            "human_review_required": True,
            "warning_count": reliability["warning_count"],
            "fail_count": reliability["fail_count"],
            "repair_count": repair_count,
            "score_breakdown": copy.deepcopy(reliability.get("score_breakdown", {})),
        }
        return final_output
