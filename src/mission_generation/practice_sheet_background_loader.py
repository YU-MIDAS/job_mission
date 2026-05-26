from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import project_path, to_posix_relative


class PracticeSheetBackgroundLoader:
    def __init__(self, root: str | Path = "data/additional_search") -> None:
        self.root = project_path(root)

    def load(self, job_cd: str) -> dict[str, Any] | None:
        path = self.root / f"{job_cd}.md"
        if not path.exists():
            return None
        return {
            "schema_version": "job_practice_sheet_background.v1",
            "job_cd": job_cd,
            "source_path": to_posix_relative(path, project_path()),
            "content_markdown": path.read_text(encoding="utf-8"),
            "usage": "background_only",
        }
