# Vibe Coding Orchestrator

An autonomous coding pipeline that uses **Notion as its task queue**, runs **Codex unattended** on implementation tasks, and hands off complex decisions to **Claude** — all for under €40/month in subscriptions.

---

## The idea

Building a complex project with AI agents usually means either babysitting a terminal or paying for expensive orchestration infrastructure. This is neither.

You plan your project with Claude. You break it into tasks in Notion. You start the orchestrator. Codex picks up implementation tasks and runs them autonomously — retrying failures, validating outputs, cascading blockers through the dependency graph. When it hits something that needs judgement (a missing credential, a design decision, a complex architectural call), it generates a Claude handoff file, notifies you, and waits. You open Claude, resolve it, mark it done. The loop continues.

No cloud infra. No task queue server. No database beyond Notion. Just a Python process, a Notion API key, and your AI subscriptions.

---

## How it works

Every loop iteration:

1. Query Notion for all agent-assigned tasks
2. Reconcile Notion state against disk reality (reset stale/lying statuses)
3. Auto-reset descendants whose blocker has cleared
4. Prepare handoff files for any Claude-assigned tasks
5. Pick the next eligible Codex task
6. Run it, validate the output artifact exists, update status

### State reconciliation

Before running anything, the orchestrator checks the filesystem against Notion:

- Task marked **Done** but file missing on disk → reset to **Todo**
- Task stuck in **Doing** → reset to **Todo** (process died mid-run)
- Task in **Blocked/Failed** with dependencies now satisfied → reset to **Todo**
- Task in any non-Done status but artifact exists → promoted to **Done**

### Dependency chains

Tasks declare dependencies in Notion. The orchestrator enforces them: a task won't run until every upstream task is Done. When a task fails, all descendants are automatically cascaded to **Blocked**. When the root cause is fixed, they reset themselves.

### Human blocker detection

After every Codex run, output is scanned for signals like missing credentials, required logins, or needed approvals. When detected, the task is marked **Waiting on Human**, descendants are blocked, and a push notification fires via ntfy.sh.

### Claude handoffs

Tasks assigned to Claude get a structured markdown handoff file at `orchestrator/handoffs/<task-id>-claude-handoff.md`. You pick it up, run a Claude session with it, mark the task Done, and the loop resumes.

---

## File structure

```
vibe_coding_orchestrator/
├── orchestrator/
│   ├── orchestrator.py        Main loop and entry point
│   ├── config.py              Env var loading and validation
│   ├── notion_client.py       Notion API client + Task dataclass
│   ├── task_selector.py       Picks the next eligible task
│   ├── task_reconciler.py     Reconciles Notion status vs disk reality
│   ├── status_updater.py      Status writes, cascade blocking, auto-reset
│   ├── codex_runner.py        Builds prompt, runs Codex subprocess
│   ├── claude_handoff.py      Generates Claude handoff markdown files
│   ├── ntfy_notifier.py       Push notifications via ntfy.sh
│   ├── logger.py              Per-attempt logs + runs.jsonl audit trail
│   ├── handoffs/              Auto-generated Claude handoff files
│   └── logs/                  Per-attempt Codex logs + runs.jsonl
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Setup

### Requirements

- Python 3.11+
- [Codex CLI](https://github.com/openai/codex) v0.114+
- A [Notion integration](https://www.notion.so/my-integrations) with an API key
- A [ntfy.sh](https://ntfy.sh) topic (free, no signup)

### Installation

```bash
git clone https://github.com/kashastic/vibe_coding_orchestrator.git
cd vibe_coding_orchestrator
pip install -e .
```

### Configuration

Copy `.env.example` to `.env` and fill in the four required values:

```
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
NTFY_TOPIC=your-topic-name
REPO_PATH=/absolute/path/to/your/project
```

Optional:
```
CODEX_COMMAND=codex
ORCHESTRATOR_CONTEXT_FILES=YourApp/claude.md,YourApp/rolling_handoff.md,YourApp/task_plan.md
ORCHESTRATOR_LOOP_SLEEP_SECONDS=2.0
CODEX_TIMEOUT_SECONDS=1800
```

### Notion database schema

Create a Notion database with these fields:

| Field | Type | Notes |
|---|---|---|
| Task | Title | Task ID + name, e.g. `M1-001 Set up project` |
| Execution Prompt | Rich Text | Instructions for the agent |
| Repo Path | Rich Text | Expected output path(s) in the repo |
| Assigned Agent | Select | `Codex` or `Claude` |
| Status | Select | `Todo`, `Doing`, `Done`, `Failed`, `Blocked`, `Waiting on Human` |
| Milestone | Select | For ordering |
| Priority | Select | For ordering within milestone |
| Dependencies | Relation or Rich Text | Comma-separated task IDs |
| Notes | Rich Text | Append-only, written by the orchestrator |

Share the database with your Notion integration. Copy the database ID from the URL.

### Context files

The orchestrator passes context files to Codex on every run. By default it looks for `claude.md`, `rolling_handoff.md`, and `task_plan.md` in your repo root (or the paths you set in `ORCHESTRATOR_CONTEXT_FILES`).

These files should contain your project's architecture, current state, and task plan. Claude maintains them as the project evolves.

### Run

```bash
python -m orchestrator
```

Optional flag: `--interactive-on-blocker` launches an interactive Codex terminal when a human blocker is detected, lets you resolve it in-place, then automatically retries.

---

## Workflow

```
1. Use Claude to plan the project → break into tasks → add to Notion
2. python -m orchestrator
3. Codex handles implementation tasks autonomously
4. When Codex hits a blocker:
   → orchestrator generates handoff file, notifies you via ntfy.sh
   → you open Claude with the handoff, resolve it, mark task Done
5. Orchestrator resumes automatically
6. Repeat until done
```

---

## Cost

- Claude Pro: ~€20/month
- Codex/OpenAI subscription: ~€18/month
- Notion: free tier works
- ntfy.sh: free

Total: under €40/month for a fully autonomous multi-agent development pipeline.

---

## License

MIT
