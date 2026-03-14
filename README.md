# Codex Orchestrator

This repository now includes a local-first orchestrator under `orchestrator/` that:

- pulls the next Codex task from the Notion database
- skips ahead to the first task whose dependencies are already `Done`
- marks it `Doing`
- sends an `ntfy.sh` start notification before Codex runs
- launches Codex locally with the task prompt
- waits for Codex to finish
- marks the task `Done` or `Blocked`
- writes run metadata and Codex output logs

## Structure

```text
orchestrator/
  orchestrator.py
  config.py
  notion_client.py
  task_selector.py
  codex_runner.py
  ntfy_notifier.py
  status_updater.py
  logger.py
  logs/                  # created at runtime
```

## Required Environment Variables

```env
NOTION_API_KEY=ntn_your_notion_integration_token_here
NOTION_DATABASE_ID=d60b1f5c-7c94-4026-8ec8-3da91423f53e
NTFY_TOPIC=your-ntfy-topic
REPO_PATH=C:\ClaudeWorkspace\JIRA_workflow_project
```

Optional:

```env
CODEX_COMMAND=codex
NOTION_VERSION=2022-06-28
```

`REPO_PATH` should point to the repo root that contains `claude.md`, `rolling_handoff.md`, and `task_plan.md`.

## Running

From the repo root:

```powershell
$env:NOTION_API_KEY="secret_..."
$env:NOTION_DATABASE_ID="d60b1f5c-7c94-4026-8ec8-3da91423f53e"
$env:NTFY_TOPIC="your-topic"
$env:REPO_PATH="C:\ClaudeWorkspace\JIRA_workflow_project"
python -m orchestrator.orchestrator
```

The orchestrator sends these notifications:

- `Codex Task Started`
- `Codex Task Finished`
- `Codex Task Failed`
- `Codex` with `All tasks completed` when the queue is empty

If the start notification cannot be delivered, the orchestrator aborts before Codex executes the task.

## Logging

- Run records are appended to `REPO_PATH/orchestrator/logs/runs.jsonl`
- Each Codex run writes stdout/stderr to `REPO_PATH/orchestrator/logs/<TASK_ID>.log`

## Notes

- The orchestrator uses the Notion API data source query endpoint because the project docs specify a Notion data source ID.
- Dependency checks are enforced before a task starts. The selector chooses the first unblocked Codex task; if all candidates are blocked, the first blocked task is marked `Blocked`.
- The Codex prompt always instructs Codex to read `claude.md`, `rolling_handoff.md`, and `task_plan.md`, inspect the repo, execute the selected task, and update the handoff files.
