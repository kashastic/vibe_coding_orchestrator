# Orchestrator Starter Prompt

Copy the prompt below and run it in a Claude session opened at your project root.

**Prerequisites before running:**
- Claude has Notion MCP access connected to your task database
- Codex CLI is installed (`npm install -g @openai/codex` or equivalent)
- The orchestrator is installed and `.env` is configured (`NOTION_API_KEY`, `NOTION_DATABASE_ID`, `REPO_PATH`, `NTFY_TOPIC`)
- Your Notion database has the required fields: Task, Execution Prompt, Repo Path, Assigned Agent, Status, Milestone, Priority, Dependencies, Notes

---

## THE PROMPT

```
You are going to plan a software project and set it up so an autonomous Codex orchestrator can build it.

Your job in this session:
1. Ask me clarifying questions (follow-up style — start with the core questions, then ask follow-ups based on my answers)
2. Once you have enough to plan, produce the full project setup:
   - Create claude.md at the repo root (architecture, decisions, file structure, module responsibilities)
   - Create task_plan.md at the repo root (full milestone and task breakdown in readable form)
   - Create rolling_handoff.md at the repo root (empty template — updated by Codex after each task)
   - Create the initial folder and file scaffold (empty files, no implementation)
   - Populate the Notion database with every task using your Notion MCP

---

### CLARIFYING QUESTIONS — ROUND 1

Ask me all of the following in a single message. Wait for my answers before asking anything else.

1. What do you want to build? (1–3 sentences)
2. Who is it for — just you, a team, or end users?
3. What does "done" look like for version 1? What's the minimum it needs to do?
4. Are there any hard requirements — specific APIs, integrations, platforms, or constraints I must respect?
5. Are there any technologies you want to use, or should I choose based on the problem?

---

### FOLLOW-UP ROUNDS

Based on my answers, ask targeted follow-up questions until you have enough to:
- Choose the technology stack with confidence
- Define the file and module structure
- Break the project into milestones (M1, M2, …)
- Write a concrete execution prompt for every task

Do not proceed to planning until you are confident in these four things. If something is still ambiguous, ask.

---

### TASK SIZING RULES

Every task you create must fit in a single Codex run. Apply these rules strictly:

- One task = one logical unit of work (one file, one module, one endpoint, one component, one config)
- The execution prompt must be self-contained: Codex reads claude.md, task_plan.md, rolling_handoff.md, and nothing else to understand what to do
- No task should require understanding the implementation details of more than 2–3 other files
- No task should produce more than ~200 lines of code
- If a task feels too large, split it

Tasks that are too large will fail. It is better to have 30 small tasks than 10 large ones.

---

### AGENT ASSIGNMENT RULES

Assign **Codex** to tasks that are:
- Pure implementation (write a file, implement a function, configure a tool)
- Well-defined with a clear expected output path
- Completable without human decisions

Assign **Claude** to tasks that are:
- Architecture decisions not resolved at planning time
- Tasks that require evaluating options before implementing
- Any task where the right answer depends on something discovered during a previous task

---

### NOTION TASK FORMAT

For every task, create a Notion page with these fields:

| Field | Value |
|---|---|
| Task (title) | `M<n>-<seq> <short task name>` e.g. `M1-001 Initialise project structure` |
| Execution Prompt | Full step-by-step instructions for the agent. Include: what to read first, what to create, what the output must look like, and how to update rolling_handoff.md when done. |
| Repo Path | The file or folder path(s) the task is expected to produce, relative to REPO_PATH. Comma-separated if multiple. |
| Assigned Agent | Codex or Claude |
| Status | Todo |
| Milestone | M1, M2, … |
| Priority | High / Medium / Low |
| Dependencies | Comma-separated task IDs of tasks that must be Done first (e.g. `M1-001, M1-002`). Leave blank if none. |
| Notes | Leave blank |

Create all tasks before finishing. Do not stop after one milestone.

---

### EXECUTION PROMPT TEMPLATE

Every Codex execution prompt must follow this structure:

```
Read these files first: claude.md, task_plan.md, rolling_handoff.md

Current task: <task name>

Context: <1–2 sentences explaining why this task exists and where it fits>

What to do:
1. <step>
2. <step>
...

Expected output: <exact file path(s) that must exist when you are done>

When done: Append a brief summary of what you did and any decisions you made to rolling_handoff.md.
```

---

### AFTER SETUP

Once you have created all files and populated Notion, tell me:
1. How many tasks were created and across how many milestones
2. Any tasks you assigned to Claude and why
3. The command to run: `python -m orchestrator`

Then I will launch the orchestrator and you are done.
```
