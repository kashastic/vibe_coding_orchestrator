# Orchestrator Setup Guide
## How to go from idea to autonomous execution

---

## How this system works

You give Claude an idea. Claude plans the project, creates all the tasks in Notion, and writes the context files your project needs. Then you run one command and the orchestrator executes everything autonomously — running Codex task by task, verifying each one worked, and notifying your phone along the way.

**Your job:** have the idea, run the command, handle the rare cases where human action is needed (a login, a missing API key, an approval).

**Claude's job:** plan the project, design the task breakdown, create the Notion board.

**Orchestrator's job:** execute the plan, manage Codex, keep Notion accurate, notify you.

---

## What you need installed

| Tool | What it is | Install |
|------|-----------|---------|
| Python 3.11+ | Runs the orchestrator | python.org |
| Codex CLI | The AI that writes the code | `npm install -g @openai/codex` |
| Git | Version control | git-scm.com |
| ntfy app | Push notifications on your phone | ntfy.sh — free |

Verify before continuing:

```powershell
python --version     # needs 3.11 or higher
codex --version      # needs to print a version
```

---

## One-time setup (do this once)

### 1. Create a Notion integration

1. Go to **https://www.notion.so/my-integrations**
2. Click **New integration**
3. Name it anything (e.g. `Orchestrator`)
4. Click **Submit**
5. Copy the **Internal Integration Secret** — it starts with `secret_`
6. Save it. You will put this in your `.env` file.

### 2. Set up ntfy on your phone

1. Install the ntfy app (iOS or Android) from **ntfy.sh**
2. Pick a topic name — any random string, e.g. `my-builds-x7k2`
   - Make it hard to guess so only you receive notifications
3. In the app, subscribe to your topic name
4. Done. The orchestrator pushes to `https://ntfy.sh/your-topic`

### 3. Copy the orchestrator into your project

Copy the `orchestrator/` folder from this repository into the root of any new project you want to automate.

```
my-new-project/
├── orchestrator/        ← copy this entire folder
├── claude.md            ← Claude creates this
├── rolling_handoff.md   ← Claude creates this
└── task_plan.md         ← Claude creates this
```

That folder is the entire engine. It requires nothing beyond Python's standard library.

---

## Starting a new project

### Step 1 — Tell Claude your idea

Open a Claude conversation and paste this to start:

```
I want to build [describe your project in plain English].

Here is how it should work:
[describe what users can do, what the app does, any tech preferences]

Please read CLAUDE_PROJECT_PLANNER.md and set up the full project for the orchestrator.
```

Claude will ask you a few clarifying questions, then:
- Design the milestones and task breakdown
- Create the Notion database with all the right fields
- Create all the tasks in Notion with execution prompts, repo paths, and dependencies
- Write `claude.md`, `rolling_handoff.md`, and `task_plan.md` in your repo
- Tell you exactly what `.env` values to fill in

### Step 2 — Create your `.env` file

Create a file called `.env` in your project root. Claude will tell you the exact values, but the format is:

```env
NOTION_API_KEY=secret_xxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NTFY_TOPIC=my-builds-x7k2
REPO_PATH=C:\path\to\my-new-project

# Optional
CODEX_COMMAND=codex
ORCHESTRATOR_CONTEXT_FILES=claude.md,rolling_handoff.md,task_plan.md
ORCHESTRATOR_LOOP_SLEEP_SECONDS=2.0
# CODEX_TIMEOUT_SECONDS=1800
```

> Add `.env` to your `.gitignore`. Never commit it.

**Where to find `NOTION_DATABASE_ID`:**
Claude will give you a link to the database it created. Open that link. The database ID is the long string of letters and numbers in the URL, between your workspace name and `?v=`:
`https://www.notion.so/yourworkspace/`**`dc46b0e161714fc89ff9be036958cae9`**`?v=...`

**Share the database with your integration:**
Claude should do this automatically. If tasks aren't loading, manually check:
- Open the database in Notion
- Click `...` top right → **Connections** → find your integration → **Connect**

### Step 3 — Load your environment variables

**Windows (PowerShell):**

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}
```

**Mac / Linux:**

```bash
set -a && source .env && set +a
```

### Step 4 — Run the orchestrator

From your project root:

```powershell
python -m orchestrator.orchestrator --interactive-on-blocker
```

That is the only command. Leave the terminal open. Watch Notion and your phone.

---

## What happens while it runs

The orchestrator loops continuously:

1. Reconciles non-`Todo` Notion task states against actual files on disk (fixes drift)
2. Picks the next eligible task (dependencies done, correct agent)
3. Marks it `Doing` in Notion
4. Sends you a start notification
5. Runs Codex with the task's execution prompt
6. Verifies the expected file was actually created
7. Marks it `Done` (or `Failed`) in Notion
8. Sends you a finish or failure notification
9. Loops

You will see output in the terminal like:

```
Task completed: M1-001 Set up project scaffold
Task completed: M1-002 Create TypeScript config
Task completed: M1-003 Implement data model
```

---

## When you get a "Waiting on Human" notification

The orchestrator has marked a task `Waiting on Human` and is continuing the loop. It will retry the task automatically on every iteration — once you fix the blocker, the next retry will succeed. Common reasons:
- A CLI tool needs you to log in (e.g. `forge login`, `aws configure`)
- An API key or credential is missing from the environment
- A manual approval or permission is required

**What to do:**
1. Read the notification — it says exactly what is needed
2. Open Notion, find the task with status `Waiting on Human`, read its `Notes` field
3. Do the thing (log in, set the env var, grant access)
4. The orchestrator will pick the task up and retry it automatically on the next loop — no manual reset needed
5. If it still fails, check `orchestrator/logs/<TASK-ID>-attempt-1.log`

**With `--interactive-on-blocker`:** instead of just continuing, the orchestrator opens an interactive Codex terminal immediately. Resolve only the blocker in that terminal, then exit it — the orchestrator retries the task automatically once the interactive session closes with exit code 0.

Important:
- the interactive Codex session is intended to resolve only the blocker
- the orchestrator remains the process that updates Notion and sends notifications
- if the orchestrator is stopped and restarted, it will resume picking up `Waiting on Human` tasks again

---

## When a task fails

Open Notion and look at the `Notes` field of the failed task. Then open the log:

```
orchestrator/logs/<TASK-ID>-attempt-1.log
```

Common issues:

| Notes field says | Fix |
|---|---|
| `expected repo path was not created` | The file Codex was supposed to make is missing. Check the log for errors. Reset task to `Todo`. |
| `Dependency X is Todo` (or `Blocked`, `Failed`, etc.) | A dependency task isn't `Done` yet. Check that upstream task's status. |
| `Codex timed out` | Task took too long. Set `CODEX_TIMEOUT_SECONDS=3600` or split the task. |
| `Notion API returned 404` | `NOTION_DATABASE_ID` is wrong, or database isn't shared with the integration. |
| `Codex CLI was not found` | `codex` is not on PATH. Run `codex --version` to check. |

To retry any task: set its `Status` back to `Todo` in Notion. The orchestrator picks it up next loop.

---

## When everything is done

The orchestrator prints `No tasks remaining.` and exits. You get an `All tasks completed` notification.

If you see `Tasks remain, but all available work is blocked` — something upstream failed and blocked the rest. Find the `Failed` tasks in Notion, fix the root cause, and reset them to `Todo`.

---

## Stopping and resuming safely

**Stop:** press `Ctrl+C`. The orchestrator exits cleanly.

**Resume:** run the same command again. The orchestrator reconciles Notion against actual files on startup. Any task that was `Doing` when you stopped gets reset to `Todo` and retried automatically. No manual cleanup needed.

---

## Log files reference

All logs are written to `orchestrator/logs/` inside your project:

| File | What it contains |
|---|---|
| `orchestrator.log` | Every status change, reconciliation event, blocker detection |
| `runs.jsonl` | Structured JSON record of every run (task id, status, duration, error) |
| `<TASK-ID>-attempt-1.log` | Full Codex stdout and stderr for that task |
| `handoffs/<TASK-ID>-claude-handoff.md` | Context file created when a task is assigned to Claude |

---

## Quick reference

| What | Command or action |
|---|---|
| Start orchestrator | `python -m orchestrator.orchestrator --interactive-on-blocker` |
| Stop orchestrator | Ctrl+C |
| Retry a failed task | Set Status to `Todo` in Notion |
| Skip a task | Set Status to `Done` in Notion manually |
| See what Codex did | `orchestrator/logs/<TASK-ID>-attempt-1.log` |
| See structured history | `orchestrator/logs/runs.jsonl` |
| Change sleep between loops | `ORCHESTRATOR_LOOP_SLEEP_SECONDS=5` in `.env` |
| Set a Codex execution timeout | `CODEX_TIMEOUT_SECONDS=1800` in `.env` |
| Change which files Codex reads | `ORCHESTRATOR_CONTEXT_FILES=myfile.md,other.md` in `.env` |
