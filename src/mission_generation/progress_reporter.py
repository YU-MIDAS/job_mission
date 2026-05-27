from __future__ import annotations

import threading

from .utils import seoul_now


class ConsoleProgressReporter:
    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self._lock = threading.Lock()

    def emit(self, message: str) -> None:
        if not self.enabled:
            return
        timestamp = seoul_now().strftime("%H:%M:%S")
        with self._lock:
            print(f"[{timestamp}] {message}", flush=True)

    def run_started(self, *, run_id: str | None, total_targets: int, concurrency: int) -> None:
        self.emit(f"run started - run_id={run_id} targets={total_targets} concurrency={concurrency}")

    def run_finished(self, *, saved_count: int, failed_count: int, repair_used_count: int) -> None:
        self.emit(f"run finished - saved={saved_count} failed={failed_count} repair_used={repair_used_count}")

    def target(
        self,
        *,
        current: int | None,
        total: int | None,
        job_cd: str,
        difficulty_code: str,
        stage: str,
        detail: str | None = None,
    ) -> None:
        if current is None or total is None:
            prefix = f"{job_cd} {difficulty_code}"
        else:
            prefix = f"[{current}/{total}] {job_cd} {difficulty_code}"
        suffix = f" - {stage}"
        if detail:
            suffix += f" ({detail})"
        self.emit(prefix + suffix)
