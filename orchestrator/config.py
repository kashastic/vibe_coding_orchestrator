from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    notion_api_key: str
    notion_database_id: str
    ntfy_topic: str
    repo_path: Path
    log_dir: Path
    run_log_path: Path
    codex_command: str = "codex"
    notion_version: str = "2022-06-28"
    context_files: tuple[str, ...] = ("claude.md", "rolling_handoff.md", "task_plan.md")
    loop_sleep_seconds: float = 2.0
    codex_timeout_seconds: int | None = None


def load_config() -> Config:
    missing = [
        name
        for name in (
            "NOTION_API_KEY",
            "NOTION_DATABASE_ID",
            "NTFY_TOPIC",
            "REPO_PATH",
        )
        if not os.getenv(name)
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_text}")

    repo_path = Path(os.environ["REPO_PATH"]).expanduser().resolve()
    if not repo_path.exists():
        raise ValueError(f"REPO_PATH does not exist: {repo_path}")
    if not repo_path.is_dir():
        raise ValueError(f"REPO_PATH is not a directory: {repo_path}")

    context_files_raw = os.getenv(
        "ORCHESTRATOR_CONTEXT_FILES", "claude.md,rolling_handoff.md,task_plan.md"
    )
    context_files = tuple(f.strip() for f in context_files_raw.split(",") if f.strip())

    missing_files = [name for name in context_files if not (repo_path / name).exists()]
    if missing_files:
        missing_text = ", ".join(missing_files)
        raise ValueError(f"REPO_PATH is missing required context files: {missing_text}")

    loop_sleep_raw = os.getenv("ORCHESTRATOR_LOOP_SLEEP_SECONDS", "2.0")
    try:
        loop_sleep_seconds = float(loop_sleep_raw)
    except ValueError:
        loop_sleep_seconds = 2.0

    codex_timeout_raw = os.getenv("CODEX_TIMEOUT_SECONDS", "")
    codex_timeout_seconds: int | None = None
    if codex_timeout_raw.strip():
        try:
            codex_timeout_seconds = int(codex_timeout_raw)
        except ValueError:
            pass

    log_dir = repo_path / "orchestrator" / "logs"

    return Config(
        notion_api_key=os.environ["NOTION_API_KEY"],
        notion_database_id=os.environ["NOTION_DATABASE_ID"],
        ntfy_topic=os.environ["NTFY_TOPIC"],
        repo_path=repo_path,
        log_dir=log_dir,
        run_log_path=log_dir / "runs.jsonl",
        codex_command=os.getenv("CODEX_COMMAND", "codex"),
        notion_version=os.getenv("NOTION_VERSION", "2022-06-28"),
        context_files=context_files,
        loop_sleep_seconds=loop_sleep_seconds,
        codex_timeout_seconds=codex_timeout_seconds,
    )
