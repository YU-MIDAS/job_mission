from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import project_path, read_json


class PracticeProfileLoadError(RuntimeError):
    pass


class PracticeProfileLoader:
    def __init__(self, root: str | Path = "resources/practice_profiles/v1") -> None:
        self.root = project_path(root)

    def load(self, job_cd: str) -> dict[str, Any] | None:
        path = self.root / f"{job_cd}.json"
        if not path.exists():
            return None
        data = read_json(path)
        self._validate(job_cd, data)
        return data

    def _validate(self, job_cd: str, data: Any) -> None:
        if not isinstance(data, dict):
            raise PracticeProfileLoadError(f"practice profile for {job_cd} must be an object")
        if data.get("schema_version") != "job_practice_profile.v1":
            raise PracticeProfileLoadError(f"invalid practice profile schema for {job_cd}")
        identity = data.get("job_identity")
        if not isinstance(identity, dict) or identity.get("job_cd") != job_cd:
            raise PracticeProfileLoadError(f"practice profile job_cd mismatch for {job_cd}")
        required_lists = [
            "practice_tasks",
            "decision_situations",
            "practice_materials",
            "collaboration_contexts",
            "response_flow",
            "deliverable_formats",
        ]
        for field in required_lists:
            if not isinstance(data.get(field), list):
                raise PracticeProfileLoadError(f"practice profile {field} must be a list for {job_cd}")
