# Codex Orchestrator

A local-first autonomous task execution engine. Claude plans the project and creates the Notion board. The orchestrator runs Codex task by task, verifies results, manages state, and notifies you on your phone.

See **ORCHESTRATOR_SETUP.md** for the full setup guide.
See **CLAUDE_PROJECT_PLANNER.md** for instructions Claude follows when planning a new project.

---

## What it does

- Pulls the next eligible task from a Notion database (respecting dependencies and priority)
- Reconciles Notion against actual repository state on every loop — repairs drift automatically
- Marks tasks `Doing`, runs Codex non-interactively, verifies the expected artifact exists
- Marks tasks `Done`, `Failed`, `Blocked`, or `Waiting on Human` based on outcome
- Blocks downstream dependent tasks automatically on failure; unblocks them when the root issue clears
- Detects human blockers (missing credentials, required logins, approvals) and optionally opens an interactive terminal to resolve them, then retries automatically
- Prepares Claude handoff bundles for Claude-assigned tasks instead of trying to execute them through Codex
- Sends push notifications via ntfy.sh at every lifecycle event
- Writes structured logs for every run

---

## Structure

```text
orchestrator/
  orchestrator.py       main control loop
  config.py             environment variable loading and validation
  notion_client.py      Notion REST API integration
  task_selector.py      dependency-aware task selection
  task_reconciler.py    repo-vs-Notion state reconciliation
  status_updater.py     Notion status writes and auto-blocking logic
  codex_runner.py       Codex subprocess execution
  claude_handoff.py     handoff file generation for Claude-assigned tasks
  ntfy_notifier.py      push notification delivery
  logger.py             structured JSONL run ledger and event log
  logs/                 created at runtime
  handoffs/             created at runtime for Claude-assigned tasks
```

---

## Environment variables

### Required

```env
NOTION_API_KEY=secret_xxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NTFY_TOPIC=your-ntfy-topic
REPO_PATH=C:\path\to\your\project
```

### Optional

```env
# Codex executable name or full path. Default: codex
CODEX_COMMAND=codex

# Notion API version. Default: 2022-06-28
NOTION_VERSION=2022-06-28

# Comma-separated context files Codex reads at the start of every task.
# Default: claude.md,rolling_handoff.md,task_plan.md
ORCHESTRATOR_CONTEXT_FILES=claude.md,rolling_handoff.md,task_plan.md

# Seconds to sleep between loop iterations. Default: 2.0
ORCHESTRATOR_LOOP_SLEEP_SECONDS=2.0

# Maximum seconds for a single Codex run before it is killed. Unset = no timeout.
# CODEX_TIMEOUT_SECONDS=1800
```

`NOTION_DATABASE_ID` must be the bare database ID from the Notion URL (the hex string before `?v=`), not the full URL.
`REPO_PATH` must contain all files listed in `ORCHESTRATOR_CONTEXT_FILES`.

---

## Running

Load environment variables, then from the project root:

```powershell
python -m orchestrator.orchestrator --interactive-on-blocker
```

`--interactive-on-blocker` opens a separate terminal window when a task needs human action (a login, a missing token, an approval) and retries the task automatically once you resolve it. Without this flag, the orchestrator marks the task `Waiting on Human` and moves on.

Important:

- the interactive Codex session is intended to resolve only the blocker, not complete the full task
- the main orchestrator process remains responsible for Notion updates and notifications
- if the orchestrator is stopped after a handoff, rerunning it can pick up `Waiting on Human` tasks again

---

## Notion reconciliation

On every loop the orchestrator cross-verifies non-`Todo` task statuses against current repo state.

Current reconciliation behavior:

- stale `Done` tasks can be moved out of `Done` if expected artifacts are missing
- stale `Doing` tasks can be recovered to `Todo` or `Blocked`
- non-`Todo` tasks can be reconciled to `Done` when expected artifacts already exist locally
- this reconciliation currently applies to tasks assigned to both `Codex` and `Claude`

---

## Task states

| State | Meaning |
|---|---|
| `Todo` | Eligible — all dependencies are `Done` |
| `Doing` | Currently executing |
| `Done` | Completed and artifact verified on disk |
| `Failed` | Codex ran but the task failed |
| `Blocked` | Cannot proceed — dependency failed or local state issue |
| `Waiting on Human` | Needs a manual action before it can continue |

---

## Notifications

The orchestrator sends these notification titles via ntfy.sh:

| Title | When |
|---|---|
| `Codex Task Started` | Task picked up and Codex is running |
| `Codex Task Finished` | Task completed successfully |
| `Codex Task Failed` | Codex ran but task failed or artifact missing |
| `Codex Task Blocked` | Task blocked before running (dependency or local state) |
| `Codex Waiting on Human` | Human action required |
| `Codex Interactive Started` | Interactive blocker session opened |
| `Codex Interactive Finished` | Interactive session exited |
| `Codex Task Resuming` | Retrying task after interactive blocker resolved |
| `Codex Blocked` | All remaining tasks are blocked — queue is stuck |
| `Codex` | All tasks completed |
| `Claude Handoff Ready` | A Claude-assigned task is ready with a handoff file |

---

## Claude handoffs

The orchestrator does not execute Claude tasks directly.

Instead, when a Claude-assigned task is ready, it creates a handoff bundle under:

```text
orchestrator/handoffs/<TASK_ID>-claude-handoff.md
```

That handoff file is intended to let a later Claude session pick up from:

- `claude.md`
- `rolling_handoff.md`
- `task_plan.md`
- current repo state
- Notion task metadata
- orchestrator logs

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | All tasks completed successfully |
| `1` | Startup error, or tasks remain but all are blocked |
| `130` | Interrupted by Ctrl+C |

---

## Logs

All logs are written under `REPO_PATH/orchestrator/logs/`:

| File | Contents |
|---|---|
| `orchestrator.log` | Every state transition, reconciliation action, blocker event |
| `runs.jsonl` | Structured JSON record per run (task id, status, duration, error) |
| `<TASK-ID>-attempt-<N>.log` | Full Codex stdout and stderr for each attempt |

---

## Notion database schema

The orchestrator expects these properties (exact names, case-sensitive):

| Property | Type | Notes |
|---|---|---|
| `Task` | Title | Task ID prefix + title, e.g. `M1-001 Set up scaffold` |
| `Status` | Select | `Todo`, `Doing`, `Done`, `Blocked`, `Failed`, `Waiting on Human` |
| `Assigned Agent` | Select | `Codex` or `Claude` |
| `Milestone` | Select | e.g. `M1`, `M2` |
| `Priority` | Select | `High`, `Medium`, `Low` |
| `Execution Prompt` | Text | Instructions sent to Codex |
| `Repo Path` | Text | Expected file/folder after task completes — used for verification |
| `Notes` | Text | Written by orchestrator on failure or human blocker |
| `Dependencies` | Relation | Self-relation to prerequisite tasks in this database |
