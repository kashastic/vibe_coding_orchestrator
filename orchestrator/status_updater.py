from __future__ import annotations

from collections import deque

from orchestrator.notion_client import NotionClient, Task

AUTO_BLOCK_PREFIX = "AUTO_BLOCKED_BY:"


class StatusUpdater:
    def __init__(self, notion_client: NotionClient) -> None:
        self._notion_client = notion_client

    def mark_todo(self, task: Task) -> None:
        self._notion_client.update_status(task.page_id, "Todo")

    def mark_doing(self, task: Task) -> None:
        self._notion_client.update_status(task.page_id, "Doing")

    def mark_done(self, task: Task) -> None:
        self._notion_client.update_status(task.page_id, "Done")

    def mark_failed(self, task: Task, reason: str) -> None:
        self._notion_client.update_status(task.page_id, "Failed")
        self._notion_client.append_note(task.page_id, reason)

    def mark_waiting_on_human(self, task: Task, reason: str) -> None:
        self._notion_client.update_status(task.page_id, "Waiting on Human")
        self._notion_client.append_note(task.page_id, reason)

    def mark_blocked(self, task: Task, reason: str) -> None:
        self._notion_client.update_status(task.page_id, "Blocked")
        self._notion_client.append_note(task.page_id, reason)

    def apply_status(self, task: Task, status: str, reason: str | None = None) -> None:
        self._notion_client.update_status(task.page_id, status)
        if reason:
            self._notion_client.append_note(task.page_id, reason)

    def block_descendants(
        self,
        *,
        root_task: Task,
        all_tasks: list[Task],
        reason: str,
        waiting_on_human: bool,
    ) -> list[Task]:
        descendants = _descendants_for(root_task, all_tasks)
        updated: list[Task] = []
        note = f"{AUTO_BLOCK_PREFIX} {root_task.task_id}\n{reason}"
        for task in descendants:
            if task.status == "Done":
                continue
            if waiting_on_human:
                self._notion_client.update_status(task.page_id, "Waiting on Human")
            else:
                self._notion_client.update_status(task.page_id, "Blocked")
            self._notion_client.append_note(task.page_id, note)
            updated.append(task)
        return updated

    def reset_auto_blocked_descendants(self, *, all_tasks: list[Task]) -> list[Task]:
        by_task_id = {task.task_id: task for task in all_tasks}
        reset: list[Task] = []
        for task in all_tasks:
            if task.status not in {"Blocked", "Waiting on Human"}:
                continue
            blocker_id = _extract_auto_blocker(task.notes)
            if blocker_id is None:
                continue
            blocker = by_task_id.get(blocker_id)
            if blocker is None:
                continue
            if blocker.status not in {"Blocked", "Waiting on Human", "Failed"}:
                self._notion_client.update_status(task.page_id, "Todo")
                cleaned = _strip_auto_block_note(task.notes, blocker_id)
                self._notion_client.set_note(task.page_id, cleaned)
                reset.append(task)
        return reset


def _descendants_for(root_task: Task, all_tasks: list[Task]) -> list[Task]:
    reverse_graph: dict[str, list[Task]] = {}
    for task in all_tasks:
        for dependency_id in task.dependency_ids:
            reverse_graph.setdefault(dependency_id, []).append(task)

    seen: set[str] = set()
    queue: deque[Task] = deque(reverse_graph.get(root_task.page_id, []))
    descendants: list[Task] = []
    while queue:
        task = queue.popleft()
        if task.page_id in seen:
            continue
        seen.add(task.page_id)
        descendants.append(task)
        queue.extend(reverse_graph.get(task.page_id, []))
    return descendants


def _extract_auto_blocker(notes: str) -> str | None:
    for line in notes.splitlines():
        if line.startswith(AUTO_BLOCK_PREFIX):
            return line.removeprefix(AUTO_BLOCK_PREFIX).strip()
    return None


def _strip_auto_block_note(notes: str, blocker_task_id: str) -> str:
    """Remove the AUTO_BLOCKED_BY marker and all following reason lines up to the next marker or blank line."""
    lines = notes.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(AUTO_BLOCK_PREFIX) and line.removeprefix(AUTO_BLOCK_PREFIX).strip() == blocker_task_id:
            i += 1  # skip the marker line itself
            # skip all non-empty, non-marker continuation lines (the reason body)
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(AUTO_BLOCK_PREFIX):
                i += 1
        else:
            result.append(line)
            i += 1
    return "\n".join(result).strip()
