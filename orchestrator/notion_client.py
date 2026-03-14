from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


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
        payload = {
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
        data = self._request_json(
            "POST", f"/data_sources/{self._database_id}/query", payload
        )
        return [self._parse_task(item) for item in data.get("results", [])]

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
        payload = {"properties": {"Notes": {"rich_text": [_text_block(next_notes)]}}}
        self._request_json("PATCH", f"/pages/{page_id}", payload)

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
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
            details = exc.read().decode("utf-8", errors="replace")
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


def _text_block(content: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": {
            "content": content,
        },
    }


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

