from __future__ import annotations

from dataclasses import dataclass

from orchestrator.notion_client import NotionClient, Task


@dataclass(frozen=True)
class SelectedTask:
    task: Task | None
    blocked_reason: str | None = None


def choose_next_task(notion_client: NotionClient) -> SelectedTask:
    tasks = notion_client.query_next_tasks()
    if not tasks:
        return SelectedTask(task=None)

    first_blocked: SelectedTask | None = None
    for task in tasks:
        blocked_reason = _dependency_blocker(notion_client, task)
        if blocked_reason is None:
            return SelectedTask(task=task)
        if first_blocked is None:
            first_blocked = SelectedTask(task=task, blocked_reason=blocked_reason)

    return first_blocked or SelectedTask(task=None)


def _dependency_blocker(notion_client: NotionClient, task: Task) -> str | None:
    for dependency_id in task.dependency_ids:
        dependency = notion_client.get_page(dependency_id)
        if dependency.status != "Done":
            dependency_label = dependency.task_id or dependency.title or dependency.page_id
            return f"Dependency {dependency_label} is {dependency.status or 'unset'}."
    return None
