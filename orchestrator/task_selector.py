from __future__ import annotations

from dataclasses import dataclass

from orchestrator.notion_client import NotionClient, Task


@dataclass(frozen=True)
class SelectedTask:
    task: Task | None
    blocked_reason: str | None = None
    has_candidates: bool = False


def choose_next_task(notion_client: NotionClient, all_tasks: list[Task]) -> SelectedTask:
    tasks = notion_client.query_next_tasks()
    if not tasks:
        return SelectedTask(task=None, has_candidates=False)

    by_page_id = {task.page_id: task for task in all_tasks}
    first_blocked: SelectedTask | None = None
    for task in tasks:
        blocked_reason = _dependency_blocker(task, by_page_id)
        if blocked_reason is None:
            return SelectedTask(task=task, has_candidates=True)
        if first_blocked is None:
            first_blocked = SelectedTask(
                task=task,
                blocked_reason=blocked_reason,
                has_candidates=True,
            )

    return first_blocked or SelectedTask(task=None, has_candidates=False)


def _dependency_blocker(task: Task, by_page_id: dict[str, Task]) -> str | None:
    for dependency_id in task.dependency_ids:
        dependency = by_page_id.get(dependency_id)
        if dependency is None:
            return f"Dependency {dependency_id} is unknown (not found in task list)."
        if dependency.status != "Done":
            dependency_label = dependency.task_id or dependency.title or dependency.page_id
            return f"Dependency {dependency_label} is {dependency.status or 'unset'}."
    return None
