from __future__ import annotations

from orchestrator.notion_client import NotionClient, Task


class StatusUpdater:
    def __init__(self, notion_client: NotionClient) -> None:
        self._notion_client = notion_client

    def mark_doing(self, task: Task) -> None:
        self._notion_client.update_status(task.page_id, "Doing")

    def mark_done(self, task: Task) -> None:
        self._notion_client.update_status(task.page_id, "Done")

    def mark_blocked(self, task: Task, reason: str) -> None:
        self._notion_client.update_status(task.page_id, "Blocked")
        self._notion_client.append_note(task.page_id, reason)

