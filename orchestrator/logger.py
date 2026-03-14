from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunRecord:
    timestamp: str
    task_id: str
    task_title: str
    status: str
    return_code: int | None
    duration_seconds: float | None
    log_path: str | None
    error: str | None


class RunLogger:
    def __init__(self, log_dir: Path, run_log_path: Path) -> None:
        self._log_dir = log_dir
        self._run_log_path = run_log_path
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._run_log_path.parent.mkdir(parents=True, exist_ok=True)

    def task_output_path(self, task_id: str) -> Path:
        safe_id = task_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
        return self._log_dir / f"{safe_id}.log"

    def append_run(self, record: RunRecord) -> None:
        with self._run_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record)) + "\n")

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def build_record(
        *,
        task_id: str,
        task_title: str,
        status: str,
        return_code: int | None,
        duration_seconds: float | None,
        log_path: Path | None,
        error: str | None,
    ) -> RunRecord:
        return RunRecord(
            timestamp=RunLogger.now_iso(),
            task_id=task_id,
            task_title=task_title,
            status=status,
            return_code=return_code,
            duration_seconds=duration_seconds,
            log_path=str(log_path) if log_path else None,
            error=error,
        )

