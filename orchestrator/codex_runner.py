from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from orchestrator.notion_client import Task


@dataclass(frozen=True)
class CodexRunResult:
    return_code: int
    duration_seconds: float
    log_path: Path

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


class CodexRunner:
    def __init__(self, codex_command: str, repo_path: Path) -> None:
        self._codex_command = codex_command
        self._repo_path = repo_path

    def build_prompt(self, task: Task) -> str:
        execution_prompt = task.execution_prompt.strip()
        repo_path_text = task.repo_path.strip() or "."
        return "\n".join(
            [
                "Execute the following workflow exactly:",
                "1. Read claude.md.",
                "2. Read rolling_handoff.md.",
                "3. Read task_plan.md.",
                "4. Inspect the current repository state before making changes.",
                "5. Execute the selected task.",
                "6. Update claude.md and rolling_handoff.md before finishing.",
                "",
                f"Repository root: {self._repo_path}",
                "",
                f"Selected task: {task.display_name}",
                f"Primary repo path: {repo_path_text}",
                "",
                "Task instructions:",
                execution_prompt if execution_prompt else "No additional task-specific prompt was provided.",
            ]
        )

    def run(self, task: Task, log_path: Path) -> CodexRunResult:
        prompt = self.build_prompt(task)
        command = self._build_command(prompt)
        start = time.monotonic()

        with log_path.open("w", encoding="utf-8") as handle:
            process = subprocess.run(
                command,
                cwd=self._repo_path,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )

        duration = time.monotonic() - start
        return CodexRunResult(
            return_code=process.returncode,
            duration_seconds=duration,
            log_path=log_path,
        )

    def _build_command(self, prompt: str) -> list[str]:
        base = shlex.split(self._codex_command, posix=False)
        if not base:
            raise ValueError("CODEX_COMMAND cannot be empty.")
        return [*base, "exec", prompt]
