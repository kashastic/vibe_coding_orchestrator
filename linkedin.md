# LinkedIn Post - Orchestrator

---

## VERSION 1: LinkedIn Post (short)

---

I built an autonomous Codex orchestrator and open-sourced it. Total cost: under €40/month using Claude and Codex subscriptions you probably already have.

**https://github.com/kashastic/vibe_coding_orchestrator**

**The workflow is this:**

You open Claude at your project root and give it a prompt describing what you want to build. Claude asks you questions until it understands the scope. Then it creates a `claude.md` architecture plan, sets up the initial file structure, populates your Notion database with a full task breakdown (dependencies, agents, milestones), and tells you to launch the orchestrator.

From that point, you step back. The orchestrator polls Notion, hands tasks to Codex one by one, validates each result, and handles everything that goes wrong. Claude planned it. Codex builds it. The orchestrator keeps them in sync.

Here's what the orchestrator handles:

**Tasks live in Notion.** Each task has a status, an assigned agent (Codex or Claude), dependencies, and an expected output path in your repo. The orchestrator polls the database in a loop.

**It reconciles state against reality before doing anything.** If a task is marked Done but the expected file doesn't exist on disk, it resets the task. If a task is stuck in Doing with no active artifact change, it recovers. No stale states survive a loop.

**Dependency chains are automatic.** A task won't run until every upstream dependency is Done. If a parent fails, all descendants are cascaded to Blocked — and when the root blocker clears, they reset themselves to Todo.

**It knows when to stop and call a human.** If Codex output signals something like "forge login required", "missing credentials", or "approval required", the orchestrator marks the task Waiting on Human, blocks its descendants, and fires a push notification via ntfy.sh. No spinning. No silent failure.

**Claude tasks get handoff files.** For tasks assigned to Claude, the orchestrator generates a structured markdown handoff and notifies you — ready to hand off to a Claude session.

**Push notifications for everything.** Task started, task done, task failed, human needed — all sent to ntfy.sh so you know what's happening without watching a terminal.

Setup is minimal: a Notion API key, the Codex CLI, an ntfy.sh topic, and a `.env` file. No cloud infra, no external task queue, no database beyond Notion.

The hardest part wasn't the happy path. It was making failure predictable: stale Doing states, missing artifacts after a "successful" run, cascading blocks that auto-unblock, and human blockers that surface clearly instead of silently rotting the queue.

Autonomous agents are only useful if you can trust their state. That's what most of the work went into.

**https://github.com/kashastic/vibe_coding_orchestrator**

#AI #DevTools #Automation #AgenticAI #OpenSource

---

## VERSION 2: LinkedIn Article (long-form)

---

# Claude Plans, Codex Builds — I Built the Orchestrator That Connects Them

Most agentic coding demos show the happy path: AI gets task, AI writes code, done.

What they don't show is who decides what the tasks are. Or what happens when a task is marked Done but the file never got created. Or when the agent silently hangs on an auth error. Or when a dependency chain falls apart and you don't find out until three tasks downstream have already run on bad assumptions.

I built a Python orchestrator that handles the full lifecycle. Claude does the planning. Codex does the building. The orchestrator manages everything in between: task state in Notion, dependency chains, failure recovery, human blocker detection, and push notifications.

Total cost: under €40/month using Claude and Codex subscriptions you probably already have.

It's open source. **https://github.com/kashastic/vibe_coding_orchestrator**

Here's everything — the full workflow from first prompt to finished project, and what each piece does.

---

## How It Actually Starts: Claude Does the Planning

Before the orchestrator runs a single task, Claude sets up the entire project.

You open Claude at your project root and give it a prompt — something like "I want to build X, here are the constraints." Claude then asks you a series of clarifying questions: What's the target platform? What's already in place? What are the hard requirements versus nice-to-haves? What integrations are needed?

Once it has enough, Claude does four things:

1. **Creates `claude.md`** — the architecture document. Technology choices, file structure, module responsibilities, design decisions. This is the document every Codex run will read first to stay oriented.
2. **Creates `rolling_handoff.md` and `task_plan.md`** — living documents that track what's been done, what's in progress, and what's coming next. Updated by Codex after every task.
3. **Populates Notion** — a full task breakdown. Each task gets an execution prompt, an expected output path, an assigned agent (Codex or Claude), a milestone, a priority, and its dependencies. The full dependency graph is set up before anything runs.
4. **Sets up the initial file structure** — repo scaffold, config files, anything that needs to exist before Codex starts.

Then you run `python -m orchestrator` and step back.

---

## The Orchestrator's Core Loop

The orchestrator is a single Python process that runs a polling loop. Every iteration:

1. Query Notion for all agent-assigned tasks
2. Reconcile Notion state against disk reality
3. Auto-reset any descendants that were blocked by a now-resolved task
4. Prepare handoff files for any Claude-assigned tasks
5. Pick the next eligible Codex task
6. Run it, validate the output, update status

No database beyond Notion. No message queue. No cloud infrastructure. Just a loop, a Notion API key, and the Codex CLI.

---

## The Notion Schema

Each task is a Notion database page with these fields:

| Field | Type | Purpose |
|---|---|---|
| Task | Title | Task ID + name, e.g. "M1-001 Set up project structure" |
| Execution Prompt | Rich Text | Full task instructions for the agent |
| Repo Path | Rich Text | Expected output file or folder path(s) in the repo |
| Assigned Agent | Select | "Codex" or "Claude" |
| Status | Select | Todo / Doing / Done / Failed / Blocked / Waiting on Human |
| Milestone | Select | Milestone grouping for ordering |
| Priority | Select | Used to order tasks within a milestone |
| Dependencies | Relation / Rich Text | Other tasks that must be Done first |
| Notes | Rich Text | Append-only notes written by the orchestrator |

Tasks are sorted by Milestone ascending, then Priority descending. The orchestrator always picks the earliest unblocked task.

---

## State Reconciliation: Trusting the Filesystem, Not Notion

Before every run, the orchestrator reconciles Notion task statuses against what actually exists on disk. This runs before any task is selected.

**The rules:**

- A task marked **Done** but whose expected file is missing on disk → reset to **Todo** (or **Blocked** if its dependencies aren't satisfied)
- A task stuck in **Doing** with no artifact on disk → reset to **Todo** (recovered stale state — the process probably died mid-run)
- A task in **Blocked** or **Failed** with all dependencies now **Done** and artifact still missing → reset to **Todo** (ready for retry)
- A task in **Blocked/Failed/Doing** whose artifact *does* exist on disk → promoted to **Done** (the work happened, Notion just didn't get updated)

This means the orchestrator can always recover from a crash, a manual edit to the database, or a run that partially succeeded. It never blindly trusts Notion — it checks the repo.

Tasks with no Repo Path field are unverifiable and are left as-is.

---

## Dependency Chain Management

The orchestrator builds a full dependency graph from the Notion database and enforces it in two places:

**Before selecting a task:** `task_selector.py` checks every dependency. If any upstream task isn't Done, the task is skipped. The first blocked task is reported as a candidate with its blocker reason.

**When a task fails:** `status_updater.py` walks the reverse dependency graph via BFS and marks every downstream task as **Blocked**, writing an `AUTO_BLOCKED_BY: <task-id>` note to each one.

**When a blocker clears:** On the next loop iteration, `reset_auto_blocked_descendants` scans all Blocked/Waiting tasks, reads their notes for the `AUTO_BLOCKED_BY` marker, looks up the blocker task's current status, and resets any task whose blocker is no longer in a failed state — back to **Todo**, with the marker note cleaned up.

This means cascading failures resolve themselves automatically when you fix the root cause. You fix one task, and the whole downstream chain resets.

---

## Running Codex

`codex_runner.py` builds a structured prompt from the task's execution prompt, the configured context files (e.g. `claude.md`, `rolling_handoff.md`, `task_plan.md`), and the expected repo path. The prompt always starts with "read these files first, then inspect current state, then execute, then update the handoff files." This keeps Codex oriented in the project context on every run.

Codex is run as a subprocess via stdin — the prompt is piped in with `--dangerously-bypass-approvals-and-sandbox exec -`. stdout and stderr are captured and written to a per-attempt log file under `orchestrator/logs/`.

**Retry logic:**

- Transient failures (network errors, `WinError 2`, executable not found) are retried up to 2 times
- Timeouts are not retried — they'd just time out again
- A successful exit code (0) stops the retry loop immediately

After a successful run, the orchestrator checks whether the expected artifact path actually exists on disk before marking the task Done. A task that exits 0 but doesn't produce the expected file is marked Failed, not Done.

---

## Human Blocker Detection

After every Codex run, the orchestrator scans the output for signals that a human needs to intervene:

| Signal phrases | Action |
|---|---|
| "forge login required", "run forge login" | Mark Waiting on Human: Forge auth missing |
| "missing api key", "missing credentials", "authorization failed" | Mark Waiting on Human: credentials missing |
| "approval required", "permission denied", "access denied" | Mark Waiting on Human: approval needed |
| "login required", "authentication required" | Mark Waiting on Human: external login needed |

When a human blocker is detected:
1. Task is marked **Waiting on Human** with the reason appended to Notes
2. All descendants are marked **Waiting on Human** (not Blocked — same cascade mechanism, different status)
3. A push notification fires via ntfy.sh with the action required

There's also an `--interactive-on-blocker` flag that launches an interactive Codex terminal to let you resolve the blocker in-place, then automatically retries the task.

---

## Claude Handoffs

Not everything can be automated. Some tasks are assigned to Claude instead of Codex — typically architecture decisions, complex reasoning tasks, or anything that needs a human in the loop.

For Claude-assigned tasks whose dependencies are all Done, the orchestrator auto-generates a markdown handoff file at `orchestrator/handoffs/<task-id>-claude-handoff.md`. The file contains:

- Task ID and title
- Execution prompt
- Repo path
- Read order for context files
- Repo root path
- Any existing notes

The task is then marked **Waiting on Human** and a push notification fires. A human picks up the handoff file and starts a Claude session with it.

---

## Push Notifications

Everything that matters sends a push notification via ntfy.sh:

- Task started
- Task completed
- Task failed (with the first 160 characters of the error)
- Human blocker detected (with the required action)
- Claude handoff ready
- All tasks blocked (no runnable work remains)
- All tasks completed

ntfy.sh is a free, open-source push notification service. You subscribe to a topic on your phone and get notifications instantly. Delivery failures are silently ignored — notifications are informational and the orchestrator never blocks on them.

---

## File Structure

```
orchestrator/
├── orchestrator.py        # Main loop and entry point
├── config.py              # Loads env vars into a frozen Config dataclass
├── notion_client.py       # Notion REST API client + Task dataclass + dependency resolution
├── task_selector.py       # Picks the next eligible task, checks dependency blockers
├── task_reconciler.py     # Reconciles Notion status vs disk reality, produces ReconcileActions
├── status_updater.py      # Writes status + notes to Notion, cascades blocks, resets descendants
├── codex_runner.py        # Builds prompt, runs Codex as subprocess, handles retries + timeouts
├── claude_handoff.py      # Generates markdown handoff files for Claude-assigned tasks
├── ntfy_notifier.py       # Sends push notifications to ntfy.sh
├── logger.py              # Per-attempt log files + runs.jsonl audit log
├── __init__.py
├── .env.example           # Template for required environment variables
├── handoffs/              # Auto-generated Claude handoff .md files (one per Claude task)
└── logs/
    ├── runs.jsonl         # JSONL audit log of every task run
    └── <task-id>-attempt-<n>.log   # Full stdout/stderr per Codex run attempt
```

**What each file is responsible for:**

`orchestrator.py` — The main loop. Orchestrates all components, handles the full run lifecycle (start → retry → validate → done/fail), detects human blockers, records all events.

`config.py` — Reads env vars, validates required fields, resolves file paths, returns a frozen `Config` dataclass. Fails fast at startup if anything is missing.

`notion_client.py` — All Notion API calls. Parses task pages into `Task` dataclasses. Handles rate limiting (HTTP 429 with Retry-After). Also resolves text-format dependency fields (comma-separated task IDs) to page IDs so the rest of the code works uniformly.

`task_selector.py` — Queries Notion for the next eligible Codex task (Todo or Waiting on Human, sorted by Milestone then Priority). Checks each candidate's dependency graph and returns the first unblocked task, or the first blocked candidate with its reason.

`task_reconciler.py` — Pure function: takes a list of tasks and the repo root, returns a list of `ReconcileAction` objects. No Notion writes — all writes go through `status_updater.py`. Also handles multi-path Repo Path fields (comma-separated) and smart path normalization for source subdirectories.

`status_updater.py` — Thin wrapper over `notion_client.py` for writes. Tracks the `AUTO_BLOCKED_BY:` note prefix convention used for cascade management. BFS traversal to find all descendants of a failed task.

`codex_runner.py` — Builds the structured execution prompt, runs Codex as a subprocess (stdin pipe mode), handles `TimeoutExpired` and `OSError`, writes per-attempt log files. Also supports launching an interactive Codex terminal for blocker resolution.

`claude_handoff.py` — Generates a standardized markdown handoff file for Claude-assigned tasks. Writes to `orchestrator/handoffs/`.

`ntfy_notifier.py` — Single HTTP POST to ntfy.sh. `try_send` swallows all errors; `send` raises `NotificationError` if needed.

`logger.py` — Writes structured events to `orchestrator.log` and appends JSONL records to `runs.jsonl` for a persistent audit trail.

---

## Setup

**Requirements:**
- Python 3.11+
- Codex CLI v0.114+ (`npm install -g @openai/codex` or equivalent)
- A Notion integration with access to your task database
- An ntfy.sh topic (free, no signup required)

**Steps:**

1. Clone the repo: `git clone https://github.com/kashastic/vibe_coding_orchestrator`
2. Install: `pip install -e .`
3. Copy `.env.example` to `.env` and fill in your values:
   - `NOTION_API_KEY` — from your Notion integration settings
   - `NOTION_DATABASE_ID` — the ID from your Notion database URL
   - `NTFY_TOPIC` — any string (e.g. `my-codex-orchestrator`)
   - `REPO_PATH` — absolute path to the repo Codex will work in
4. Create context files in your repo root: `claude.md`, `rolling_handoff.md`, `task_plan.md` (or configure `ORCHESTRATOR_CONTEXT_FILES` to point to your own)
5. Set up your Notion database with the required fields (Task, Execution Prompt, Repo Path, Assigned Agent, Status, Dependencies)
6. Run: `python -m orchestrator`

Optional: `--interactive-on-blocker` to launch interactive Codex sessions when human blockers are detected.

---

## Why Not Just Use a Real Task Queue?

Because I don't want to run one. The whole point is that this system has no moving parts beyond a Python process and two API keys. Notion is already where I manage tasks. Using it as the task queue means I can edit tasks, add dependencies, change priorities, and inspect state from any device — without any special tooling.

The tradeoff is that Notion isn't built for this. It doesn't have atomic status transitions or guaranteed delivery. The reconciliation loop is what compensates for that: instead of relying on Notion as a source of truth, it treats Notion as a human-readable view and the filesystem as the ground truth.

---

## The Part That Actually Took Time

The happy path is easy. You build the prompt, run Codex, mark Done.

What took real engineering effort was making failure modes predictable and recoverable:

- **Stale Doing states** — if the process dies while a task is running, the task stays in Doing forever unless something resets it. Reconciliation handles this.
- **Silent artifact failures** — Codex exits 0 but the file never gets written. Post-run validation catches this and marks Failed.
- **Cascading blocks** — a single failed task can invalidate everything downstream. The cascade system handles this automatically, and unblocks automatically when the root cause is fixed.
- **Human blockers that rot silently** — without explicit detection, an auth error just looks like a failure. The blocker detection system surfaces it with a specific action and stops spinning.

Autonomous agents are only useful if you can trust their state. Everything here is designed around that principle.

**https://github.com/kashastic/vibe_coding_orchestrator**

#AI #DevTools #Automation #AgenticAI #OpenSource #Python #Codex
