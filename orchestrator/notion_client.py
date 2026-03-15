from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request

_RATE_LIMIT_MAX_RETRIES = 3


class NotionAPIError(RuntimeError):
    """Raised when the Notion API returns an error or invalid response."""


@dataclass(frozen=True)
class Task:
    page_id: str
    task_id: str
    title: str
    execution_prompt: str
    repo_path: str
    assigned_agent: str
    status: str | None
    milestone: str | None
    priority: str | None
    notes: str
    dependency_ids: tuple[str, ...]
    raw_properties: dict[str, Any]

    @property
    def display_name(self) -> str:
        return f"{self.task_id} {self.title}".strip()


class NotionClient:
    def __init__(self, api_key: str, database_id: str, notion_version: str) -> None:
        self._api_key = api_key
        self._database_id = database_id
        self._notion_version = notion_version
        self._base_url = "https://api.notion.com/v1"

    def query_next_tasks(self) -> list[Task]:
        return self._query_tasks(
            {
                "filter": {
                    "and": [
                        {
                            "property": "Assigned Agent",
                            "select": {
                                "equals": "Codex",
                            },
                        },
                        {
                            "or": [
                                {
                                    "property": "Status",
                                    "select": {
                                        "equals": "Todo",
                                    },
                                },
                                {
                                    "property": "Status",
                                    "select": {
                                        "equals": "Waiting on Human",
                                    },
                                },
                                {
                                    "property": "Status",
                                    "select": {
                                        "is_empty": True,
                                    },
                                },
                            ],
                        },
                    ]
                },
                "sorts": [
                    {"property": "Milestone", "direction": "ascending"},
                    {"property": "Priority", "direction": "descending"},
                ],
                "page_size": 20,
            }
        )

    def query_codex_tasks(self) -> list[Task]:
        return self.query_tasks_for_agents(("Codex",))

    def query_tasks_for_agents(self, agent_names: tuple[str, ...]) -> list[Task]:
        if not agent_names:
            return []
        if len(agent_names) == 1:
            filter_payload: dict[str, Any] = {
                "property": "Assigned Agent",
                "select": {
                    "equals": agent_names[0],
                },
            }
        else:
            filter_payload = {
                "or": [
                    {
                        "property": "Assigned Agent",
                        "select": {
                            "equals": agent_name,
                        },
                    }
                    for agent_name in agent_names
                ]
            }
        return self._query_tasks(
            {
                "filter": filter_payload,
                "page_size": 100,
            }
        )

    def _query_tasks(self, payload: dict[str, Any]) -> list[Task]:
        results: list[Task] = []
        next_cursor: str | None = None
        while True:
            current_payload = dict(payload)
            if next_cursor is not None:
                current_payload["start_cursor"] = next_cursor
            data = self._request_json(
                "POST", f"/databases/{self._database_id}/query", current_payload
            )
            results.extend(self._parse_task(item) for item in data.get("results", []))
            if not data.get("has_more"):
                break
            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break
        return _resolve_text_dependencies(results)

    def get_page(self, page_id: str) -> Task:
        data = self._request_json("GET", f"/pages/{page_id}")
        return self._parse_task(data)

    def update_status(self, page_id: str, status: str) -> None:
        payload = {"properties": {"Status": {"select": {"name": status}}}}
        self._request_json("PATCH", f"/pages/{page_id}", payload)

    def append_note(self, page_id: str, note: str) -> None:
        page = self.get_page(page_id)
        existing_notes = page.notes.strip()
        next_notes = f"{existing_notes}\n{note}".strip() if existing_notes else note
        payload = {"properties": {"Notes": {"rich_text": _make_text_blocks(next_notes)}}}
        self._request_json("PATCH", f"/pages/{page_id}", payload)

    def set_note(self, page_id: str, note: str) -> None:
        payload = {"properties": {"Notes": {"rich_text": _make_text_blocks(note)}}}
        self._request_json("PATCH", f"/pages/{page_id}", payload)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        _retries_left: int = _RATE_LIMIT_MAX_RETRIES,
    ) -> dict[str, Any]:
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            f"{self._base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Notion-Version": self._notion_version,
            },
        )

        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429 and _retries_left > 0:
                try:
                    retry_after = int(exc.headers.get("Retry-After", "1"))
                except (TypeError, ValueError):
                    retry_after = 1
                time.sleep(max(retry_after, 1))
                return self._request_json(method, path, payload, _retries_left=_retries_left - 1)
            details = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                raise NotionAPIError(
                    "Notion API returned 404 for "
                    f"{method} {path}. Verify that NOTION_DATABASE_ID is the database ID "
                    "from the Notion database URL and that the database has been shared "
                    "with your integration."
                ) from exc
            raise NotionAPIError(
                f"Notion API {method} {path} failed with {exc.code}: {details}"
            ) from exc
        except error.URLError as exc:
            raise NotionAPIError(f"Notion API {method} {path} network error: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise NotionAPIError(f"Notion API {method} {path} returned invalid JSON") from exc

    def _parse_task(self, page: dict[str, Any]) -> Task:
        properties = page.get("properties", {})
        title = _extract_title(properties, "Task")
        task_id = _extract_task_id(title)
        return Task(
            page_id=page["id"],
            task_id=task_id,
            title=title,
            execution_prompt=_extract_rich_text(properties, "Execution Prompt"),
            repo_path=_extract_rich_text(properties, "Repo Path"),
            assigned_agent=_extract_select_name(properties, "Assigned Agent") or "",
            status=_extract_select_name(properties, "Status"),
            milestone=_extract_select_name(properties, "Milestone")
            or _extract_rich_text(properties, "Milestone"),
            priority=_extract_select_name(properties, "Priority"),
            notes=_extract_rich_text(properties, "Notes"),
            dependency_ids=tuple(_extract_relation_ids(properties, "Dependencies")),
            raw_properties=properties,
        )


_NOTION_BLOCK_LIMIT = 2000


def _text_block(content: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": {
            "content": content,
        },
    }


def _make_text_blocks(content: str) -> list[dict[str, Any]]:
    """Split content into chunks that respect Notion's 2000-character per block limit."""
    if not content:
        return []
    return [
        _text_block(content[i : i + _NOTION_BLOCK_LIMIT])
        for i in range(0, len(content), _NOTION_BLOCK_LIMIT)
    ]


def _extract_title(properties: dict[str, Any], name: str) -> str:
    prop = properties.get(name, {})
    parts = prop.get("title", [])
    return "".join(part.get("plain_text", "") for part in parts).strip()


def _extract_rich_text(properties: dict[str, Any], name: str) -> str:
    prop = properties.get(name, {})
    parts = prop.get("rich_text", [])
    return "".join(part.get("plain_text", "") for part in parts).strip()


def _extract_select_name(properties: dict[str, Any], name: str) -> str | None:
    prop = properties.get(name, {})
    select = prop.get("select")
    if isinstance(select, dict):
        return select.get("name")
    return None


def _extract_relation_ids(properties: dict[str, Any], name: str) -> list[str]:
    prop = properties.get(name, {})
    relation = prop.get("relation", [])
    return [item["id"] for item in relation if "id" in item]


def _extract_task_id(title: str) -> str:
    if " " not in title:
        return title
    maybe_id = title.split(" ", 1)[0].strip()
    return maybe_id


def _resolve_text_dependencies(tasks: list[Task]) -> list[Task]:
    """Resolve text-format dependency IDs to page IDs.

    When the Notion Dependencies field is plain text (e.g. "M1-001, M2-003")
    rather than a Relation property, _extract_relation_ids returns an empty
    list.  This function reads the raw text value from raw_properties, parses
    the comma-separated task IDs, and replaces dependency_ids with the
    corresponding page IDs looked up from the task list itself.

    Tasks that already have relation-based dependency_ids are left unchanged.
    Text values that start with "none" or cannot be resolved are ignored.
    """
    from dataclasses import replace as dc_replace

    by_task_id = {task.task_id: task.page_id for task in tasks}
    resolved: list[Task] = []
    for task in tasks:
        if task.dependency_ids:
            resolved.append(task)
            continue
        raw_text = _extract_rich_text(task.raw_properties, "Dependencies")
        if not raw_text or raw_text.lower().startswith("none"):
            resolved.append(task)
            continue
        dep_page_ids: list[str] = []
        for part in raw_text.replace(";", ",").split(","):
            dep_task_id = part.strip()
            page_id = by_task_id.get(dep_task_id)
            if page_id:
                dep_page_ids.append(page_id)
        if dep_page_ids:
            resolved.append(dc_replace(task, dependency_ids=tuple(dep_page_ids)))
        else:
            resolved.append(task)
    return resolved
