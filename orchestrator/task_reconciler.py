from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orchestrator.notion_client import Task


@dataclass(frozen=True)
class ReconcileAction:
    task: Task
    target_status: str
    reason: str


def plan_reconciliation(tasks: list[Task], repo_root: Path) -> list[ReconcileAction]:
    by_page_id = {task.page_id: task for task in tasks}
    actions: list[ReconcileAction] = []
    for task in tasks:
        if task.assigned_agent not in {"Codex", "Claude"}:
            continue

        dependencies_done = all(
            by_page_id.get(dependency_id) is not None
            and by_page_id[dependency_id].status == "Done"
            for dependency_id in task.dependency_ids
        )
        has_artifact_path = bool(task.repo_path.strip())
        artifact_exists = task_artifact_exists(task, repo_root)
        current_status = task.status or "Todo"

        if current_status == "Done":
            # Only challenge "Done" when we have a path to verify AND the artifact is absent.
            # Tasks with no Repo Path are unverifiable — trust their Done status unconditionally.
            if has_artifact_path and not artifact_exists:
                next_status = "Todo" if dependencies_done else "Blocked"
                actions.append(
                    ReconcileAction(
                        task=task,
                        target_status=next_status,
                        reason=_reason_for_missing_artifact(task, next_status),
                    )
                )
            continue

        if current_status in {"Doing", "Blocked", "Failed", "Waiting on Human"}:
            # Promote to Done only when we can positively verify the artifact exists.
            # Tasks with no Repo Path are unverifiable — never auto-promote them.
            if has_artifact_path and artifact_exists:
                actions.append(
                    ReconcileAction(
                        task=task,
                        target_status="Done",
                        reason="Reconciled from repository state: expected task artifacts exist locally.",
                    )
                )
                continue

            if current_status == "Doing":
                next_status = "Todo" if dependencies_done else "Blocked"
                actions.append(
                    ReconcileAction(
                        task=task,
                        target_status=next_status,
                        reason="Recovered stale Doing status: no active artifact change was found for the task.",
                    )
                )
                continue

            if current_status in {"Blocked", "Failed"} and dependencies_done:
                actions.append(
                    ReconcileAction(
                        task=task,
                        target_status="Todo",
                        reason="Reconciled for retry: dependencies are satisfied and expected artifacts are still missing.",
                    )
                )

    return actions


def task_artifact_exists(task: Task, repo_root: Path) -> bool:
    """Return True if all declared repo paths exist, or if no repo path is declared (unverifiable)."""
    repo_paths = _expand_repo_paths(task.repo_path)
    if not repo_paths:
        return True  # Nothing to verify — treat as satisfied (used for post-execution validation)
    return all(_path_exists(path, repo_root) for path in repo_paths)


def _reason_for_missing_artifact(task: Task, next_status: str) -> str:
    if next_status == "Blocked":
        return "Reconciled from repository state: task was marked Done, but its artifact is missing and dependencies are not fully satisfied."
    return "Reconciled from repository state: task was marked Done, but its expected artifact is missing locally."


def _expand_repo_paths(repo_path: str) -> list[str]:
    raw_parts = [part.strip() for part in repo_path.split(",") if part.strip()]
    if not raw_parts:
        return []

    normalized_parts: list[str] = []
    current_root: str | None = None
    for part in raw_parts:
        cleaned = _clean_repo_path(part)
        path_obj = Path(cleaned)
        if len(path_obj.parts) >= 2:
            current_root = path_obj.parts[0]
            normalized_parts.append(cleaned)
        elif current_root is not None and not path_obj.is_absolute():
            normalized_parts.append(str(Path(current_root) / path_obj))
        else:
            normalized_parts.append(cleaned)
    return normalized_parts


def _clean_repo_path(path_text: str) -> str:
    cleaned = path_text.replace("`", "").strip()
    if "(" in cleaned:
        cleaned = cleaned.split("(", 1)[0].strip()
    return cleaned.rstrip("/")


def _path_exists(path_text: str, repo_root: Path) -> bool:
    if any(symbol in path_text for symbol in ("*", "?", "[")):
        return any(repo_root.glob(path_text))
    candidate = repo_root / Path(path_text)
    return candidate.exists()
