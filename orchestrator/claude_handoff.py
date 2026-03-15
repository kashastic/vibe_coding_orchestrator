from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orchestrator.notion_client import Task


@dataclass(frozen=True)
class ClaudeHandoff:
    task: Task
    path: Path


def build_handoff(task: Task, repo_root: Path, output_dir: Path) -> ClaudeHandoff:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{task.task_id}-claude-handoff.md"
    content = "\n".join(
        [
            f"# Claude Handoff: {task.task_id}",
            "",
            f"Task: {task.display_name}",
            f"Assigned Agent: {task.assigned_agent}",
            f"Repo Path: {task.repo_path or '(not specified)'}",
            "",
            "Read in order:",
            "1. claude.md",
            "2. rolling_handoff.md",
            "3. task_plan.md",
            "",
            "Task prompt:",
            task.execution_prompt or "(no execution prompt provided)",
            "",
            "Notes:",
            task.notes or "(none)",
            "",
            f"Repository root: {repo_root}",
            "",
            "Claude should use this handoff together with current repo state and the latest project memory files.",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return ClaudeHandoff(task=task, path=path)
