# Orchestrator Starter Prompt

This is a two-phase workflow. Phase 1 is planning — you and Claude, before the orchestrator ever runs. Phase 2 is execution — the orchestrator runs Codex autonomously on the finalized task list.

**This prompt covers Phase 1 only.**

---

## Phase 1: Planning (you + Claude)

Copy the prompt below and run it in a Claude session opened at your project root.

**Prerequisites:**
- Claude has Notion MCP access connected to your task database
- Your Notion database has the required fields: Task, Execution Prompt, Repo Path, Assigned Agent, Status, Milestone, Priority, Dependencies, Notes
- Codex CLI is installed (`npm install -g @openai/codex` or equivalent)
- The orchestrator is installed and `.env` is configured (`NOTION_API_KEY`, `NOTION_DATABASE_ID`, `REPO_PATH`, `NTFY_TOPIC`)

---

## THE PROMPT

```
You are going to plan a software project from scratch.

Your job in this session is to understand what I want to build, make all the key architecture decisions with me, and then produce everything needed so a Codex orchestrator can build it autonomously.

This is a planning session — you and I are doing the thinking now, so Codex doesn't have to. Every decision that can be made upfront should be made here.

---

### STEP 1 — CLARIFYING QUESTIONS (ROUND 1)

Ask me all of the following in a single message. Wait for my answers before proceeding.

1. What do you want to build? (1–3 sentences)
2. Who is it for — just you, a team, or end users?
3. What does "done" look like for version 1? What's the minimum it needs to do?
4. Are there any hard requirements — specific APIs, integrations, platforms, or constraints I must respect?
5. Are there any technologies you want to use, or should I choose based on the problem?

---

### STEP 2 — FOLLOW-UP ROUNDS

Based on my answers, ask targeted follow-up questions until you are confident enough to:
- Choose the full technology stack
- Define every file and module in the project
- Break the work into milestones (M1, M2, …)
- Write a concrete, self-contained execution prompt for every task

Do not move to planning until you can answer all four. If anything is still ambiguous, ask.

---

### STEP 3 — PROJECT SETUP

Once you have enough, produce the following:

1. **claude.md** at the repo root
   - Technology choices and why
   - Full file and folder structure with one-line descriptions
   - Module responsibilities and boundaries
   - Key design decisions made in this session
   - Anything Codex must know to stay consistent across tasks

2. **task_plan.md** at the repo root
   - Full milestone and task breakdown in readable form
   - For each task: ID, name, what it produces, dependencies

3. **rolling_handoff.md** at the repo root
   - Empty template. Codex appends a summary after every task it completes.
   - Start with a single line: `# Rolling Handoff\n\n(Codex appends a summary here after each completed task.)`

4. **Initial file scaffold**
   - Create empty placeholder files for every file in the project structure
   - No implementation — just the structure so Codex has the full picture from task one

5. **Notion tasks** — create every task in the Notion database using your Notion MCP

---

### TASK SIZING RULES

Every task must fit in a single Codex run without needing a large context window. Apply strictly:

- One task = one logical unit (one file, one module, one endpoint, one component, one config)
- The execution prompt must be fully self-contained: Codex reads claude.md, task_plan.md, rolling_handoff.md — nothing else
- No task should require understanding the internals of more than 2–3 other files
- No task should produce more than ~200 lines of code
- If a task feels too large, split it

30 small tasks beat 10 large ones. Large tasks fail.

---

### AGENT ASSIGNMENT RULES

Almost all tasks should be assigned to **Codex**. Codex handles everything that is:
- Pure implementation (write a file, implement a function, configure a tool)
- Well-defined with a clear expected output path
- Completable without a new decision being made

Only assign **Claude** to a task if it genuinely cannot be decided now — for example, if the right approach depends on something that can only be known after earlier tasks complete and a human needs to evaluate the result. These should be rare. If you find yourself assigning many tasks to Claude, you haven't planned deeply enough — go back and make those decisions now.

---

### NOTION TASK FORMAT

For every task, create a Notion page with these exact fields:

| Field | Value |
|---|---|
| Task (title) | `M<n>-<seq> <short task name>` — e.g. `M1-001 Initialise project structure` |
| Execution Prompt | Full instructions for Codex. Include: what to read first, what to create, what the output must look like, and how to update rolling_handoff.md when done. |
| Repo Path | File or folder path(s) the task is expected to produce, relative to REPO_PATH. Comma-separated if multiple. |
| Assigned Agent | Codex (or Claude only if truly unavoidable — see above) |
| Status | Todo |
| Milestone | M1, M2, … |
| Priority | High / Medium / Low |
| Dependencies | Comma-separated task IDs that must be Done first. Leave blank if none. |
| Notes | Leave blank |

Create every task across all milestones before finishing.

---

### EXECUTION PROMPT TEMPLATE

Every task's execution prompt must follow this structure:

```
Read these files first: claude.md, task_plan.md, rolling_handoff.md

Current task: <task name>

Context: <1–2 sentences explaining why this task exists and where it fits in the project>

What to do:
1. <step>
2. <step>
...

Expected output: <exact file path(s) that must exist when you are done>

When done: Append a brief summary of what you did and any decisions you made to rolling_handoff.md.
```

---

### STEP 4 — HANDOFF TO HUMAN

Once all files are created and all tasks are in Notion, give me:
1. Total task count and milestone breakdown
2. Any tasks assigned to Claude and the specific reason why they couldn't be decided now
3. Anything I should review or double-check before launching the orchestrator

Stop here. Do not launch anything. The human reviews first.
```

---

## Phase 2: Review (you, before launching the orchestrator)

Before running the orchestrator, go through Notion and:

- Read every task. Does the execution prompt make sense? Is it sized correctly?
- Edit tasks that are too vague or too large
- Add tasks that are missing
- Remove tasks that are redundant
- Reorder dependencies if needed
- Work with Claude to refine anything that feels off

**Only launch the orchestrator once you are satisfied with the full task list.**

---

## Phase 3: Execution (orchestrator)

```bash
python -m orchestrator
```

The orchestrator takes it from here. It executes Codex tasks in dependency order, validates each output, handles failures, and notifies you when something needs your attention.
