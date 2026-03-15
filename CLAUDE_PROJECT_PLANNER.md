# Claude Project Planner
## Instructions for setting up a new project for the orchestrator

When a user asks you to set up a project for the orchestrator, follow this document exactly.
Your job is to go from the user's idea to a fully ready Notion board and repo context files.
The user should be able to run the orchestrator immediately after you finish.

---

## Step 1 — Understand the project

Before planning anything, ask the user these questions if they haven't answered them:

1. **What are you building?** (one paragraph is fine)
2. **What technology stack?** (language, framework, platform — or tell me and I'll recommend)
3. **What does "done" look like for version 1?** (what can a user do when it's working)
4. **Are there any hard constraints?** (no certain libraries, must run on X platform, etc.)
5. **Where is the project folder?** (full path, e.g. `C:\Projects\my-app` or `/home/user/my-app`)

Do not start creating tasks until you have clear answers to all five.

---

## Step 2 — Design the milestone and task breakdown

### Milestone rules

- Group tasks into milestones by concern, not by time
- Milestone 0 (M0) is always architecture and planning — Codex reads this, no code produced
- Milestone 1 (M1) is always scaffolding — project structure, configs, dependency files
- Later milestones are feature implementation in dependency order
- Typical project has 4–8 milestones
- Name milestones descriptively: `M1 - Project Scaffold`, `M2 - Data Model`, `M3 - API Layer`

### Task rules

- One task = one file created or one clearly bounded change to one file
- If a task touches more than two files, split it
- Target 5–20 minutes of Codex work per task
- Every task must have a clear, verifiable output
- Tasks within a milestone run in order; across milestones, dependency links enforce order
- Naming convention: `M1-001 Task title`, `M1-002 Task title`, etc.
- ID format: milestone letter+number dash zero-padded three-digit sequence

### Dependency rules

- Only link dependencies that are actually needed — do not link everything sequentially
- A task needs a dependency when it imports from, extends, or configures something the other task creates
- Types first, then implementations that use those types
- Shared configs before everything that reads them
- Foundation files before files that build on them

### Agent assignment rules

- Assign `Codex` to all implementation tasks (creating files, writing code)
- Assign `Claude` to tasks that require judgment, review, planning, or documentation that benefits from this conversation's context
- Most tasks should be `Codex`

---

## Step 3 — Write the Execution Prompt for each task

This is the most important field. Codex reads this and does exactly what it says. Be precise.

### Good Execution Prompt structure

```
Create the file <exact/path/to/file.ts>.

Requirements:
- [specific requirement 1]
- [specific requirement 2]
- [specific requirement 3]

Constraints:
- [no any types, no default exports, etc.]
- [follow patterns in X if X already exists]
```

### What makes a good prompt

- **State the output file path explicitly.** Never say "create a file" — say "create `src/types/user.ts`".
- **List requirements as bullets.** Each bullet is one thing the file must do or contain.
- **State constraints explicitly.** Do not assume Codex knows your conventions.
- **Reference existing files when relevant.** "Follow the pattern established in `src/api/base.ts`."
- **Include the interface/function signatures when known.** The more specific, the fewer failures.
- **Never ask Codex to "figure it out"** — it will guess and the guess may be wrong.

### Bad prompt (too vague)
```
Create the user authentication module.
```

### Good prompt (specific)
```
Create the file src/auth/validator.ts.

Requirements:
- Export a function validateToken(token: string): Promise<TokenPayload | null>
- TokenPayload should be imported from src/types/auth.ts
- Use the jose library for JWT verification
- Read the JWT_SECRET from process.env — throw if missing at module load time
- Return null (not throw) when the token is invalid or expired

Constraints:
- No default exports
- No any types — use unknown and narrow where needed
- Do not import from src/api/ — this module must have no circular dependencies
```

---

## Step 4 — Set the Repo Path for each task

The orchestrator verifies this path exists on disk after Codex finishes. If the file is missing, the task is marked Failed even if Codex exited cleanly. Set it correctly.

| Situation | What to put in Repo Path |
|---|---|
| Task creates a single file | `AppName/src/auth/validator.ts` |
| Task creates a folder with multiple files | `AppName/src/components/` |
| Task creates multiple specific files | `AppName/src/types/user.ts, AppName/src/types/post.ts` |
| Task modifies an existing file | the path to that file (including AppName/ prefix) |
| Task is planning/architecture only | leave blank |
| Task produces no file artifact | leave blank |

Multiple paths are comma-separated. Glob patterns are supported: `src/resolvers/*.ts`

If Repo Path is blank, the orchestrator trusts Codex's exit code and does not verify anything.

---

## Step 5 — Create the Notion database

Use the Notion MCP tools to create the database. The schema must match exactly.

### Required properties (exact names, exact types)

| Property name | Property type | Required options |
|---|---|---|
| `Task` | Title | *(default, always exists)* |
| `Status` | Select | `Todo`, `Doing`, `Done`, `Blocked`, `Failed`, `Waiting on Human` |
| `Assigned Agent` | Select | `Codex`, `Claude` |
| `Milestone` | Select | one option per milestone, e.g. `M1`, `M2`, `M3` |
| `Priority` | Select | `High`, `Medium`, `Low` |
| `Execution Prompt` | Text (rich text) | *(none)* |
| `Repo Path` | Text (rich text) | *(none)* |
| `Notes` | Text (rich text) | *(none)* |
| `Dependencies` | Relation | self-relation back to this same database |

Property names are case-sensitive. `Execution Prompt` is not `execution_prompt`. Get them exactly right.

### After creating the database

Share it with the user's Notion integration immediately. The user's integration name is the one they created at https://www.notion.so/my-integrations. Ask the user for its name if you don't know it.

---

## Step 6 — Create all the task pages in Notion

Create one page per task. For each page set:

- **Title (`Task` field):** `M1-001 Task title` — always include the ID prefix
- **Status:** `Todo`
- **Assigned Agent:** `Codex` or `Claude`
- **Milestone:** e.g. `M1`
- **Priority:** `High`, `Medium`, or `Low`
- **Execution Prompt:** the full prompt you wrote in Step 3
- **Repo Path:** the path(s) from Step 4
- **Dependencies:** link to the Notion pages of prerequisite tasks

Create all tasks before linking dependencies, since you need the page IDs.

---

## Step 7 — Create the three context files in the repo

These are written into the **application subfolder** (`AppName/`) inside the project root — not the project root itself. The subfolder name matches the application name. Codex reads them at the start of every task to understand the project.

### `claude.md`

```markdown
# claude.md - Project Memory
# [Project Name]

> Claude updates this file after every milestone or architectural decision.
> Codex reads this first before doing anything.

---

## Project

**Name:** [Project Name]
**Goal:** [One sentence describing what is being built]
**Stack:** [Language, framework, platform]
**Repo:** [full path to project root]

---

## Mission

[Two to three sentences describing what the final product does and who uses it.]

---

## Current Goal

**Phase:** Implementation in progress
**Active Milestone:** M1 - [Milestone name]
**Next Task:** M1-001

---

## Architecture

[Describe the high-level structure. Where does each concern live?
What are the main modules? How does data flow?
Keep this to one or two paragraphs. Update it as decisions are made.]

---

## Repository Layout

[Show the intended folder structure as a tree. Include src/, any config files, etc.]

---

## Progress

| Milestone | Name | Status |
|---|---|---|
| M1 | [Name] | In Progress |
| M2 | [Name] | Todo |

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| [e.g. State management] | [e.g. Context + useReducer] | [e.g. Scope does not justify Redux] |

---

## Hard Rules for Codex

[List project-specific rules. Examples:]
- Never use `any` — use `unknown` with narrowing
- Never put business logic in React components
- Never use History API — use hash routing
- [Add your own]

---

## Codex Entry Procedure

1. Read `claude.md`.
2. Read `rolling_handoff.md`.
3. Read `task_plan.md`.
4. Inspect the current repository state before making changes.
5. Execute the selected task.
6. Update `claude.md` and `rolling_handoff.md` before finishing.
```

### `rolling_handoff.md`

```markdown
# rolling_handoff.md - Rolling Handoff
# [Project Name]

> Codex reads this second, after claude.md.
> Keep this file concise and current. Update it after every completed task.

---

## Last Updated

**Date:** [today's date]
**By:** Claude
**Action:** Initial project setup. Notion board created. Context files written.

---

## Current Milestone

**M1 - [Milestone Name]**
Status: Ready to start. Repository is empty.

---

## Next Three Tasks

### 1. M1-001 - [Task title]
[One line description]

### 2. M1-002 - [Task title]
[One line description]

### 3. M1-003 - [Task title]
[One line description]

---

## Blockers

None.

---

## Architecture Decisions Log

| Date | Decision | Reason |
|---|---|---|
| [today] | [e.g. Chose X over Y] | [reason] |
```

### `task_plan.md`

```markdown
# task_plan.md - Task Plan
# [Project Name]

---

## Milestone 1 — [Name]

| ID | Task | Status | Agent | Repo Path |
|---|---|---|---|---|
| M1-001 | [Title] | Todo | Codex | [path] |
| M1-002 | [Title] | Todo | Codex | [path] |

---

## Milestone 2 — [Name]

| ID | Task | Status | Agent | Repo Path |
|---|---|---|---|---|
| M2-001 | [Title] | Todo | Codex | [path] |
```

---

## Step 8 — Tell the user what to do next

After creating the Notion board and repo files, give the user:

1. **The database URL** — so they can find it and get the ID
2. **The database ID** — extracted from the URL (the hex string before `?v=`)
3. **The `.env` file contents** — filled in with their API key placeholder, the real database ID, the real repo path, and `ORCHESTRATOR_CONTEXT_FILES=AppName/claude.md,AppName/rolling_handoff.md,AppName/task_plan.md`
4. **The exact command to run** — `python -m orchestrator.orchestrator --interactive-on-blocker`
5. **A summary of what was created** — how many tasks, how many milestones, what order they run in

---

## Checklist before handing off to the user

- [ ] All 9 Notion database properties created with exact names and types
- [ ] Status field has all 6 required values: `Todo`, `Doing`, `Done`, `Blocked`, `Failed`, `Waiting on Human`
- [ ] Database shared with the user's Notion integration
- [ ] All tasks created with Title, Status=Todo, Assigned Agent, Milestone, Priority, Execution Prompt
- [ ] All tasks that produce files have Repo Path filled in
- [ ] All dependency links created
- [ ] `AppName/claude.md` written to the application subfolder
- [ ] `AppName/rolling_handoff.md` written to the application subfolder
- [ ] `AppName/task_plan.md` written to the application subfolder
- [ ] User has the database ID
- [ ] User has the `.env` template with real values filled in
- [ ] User knows the run command

---

## What NOT to do

- Do not create tasks that are too vague — if you cannot write a specific Execution Prompt, the task needs to be split or clarified
- Do not create tasks with no Repo Path for implementation work — every file Codex creates should be verifiable
- Do not chain all tasks sequentially with dependencies unless they actually depend on each other — this creates an artificial bottleneck
- Do not assign tasks to Claude unless the task genuinely requires judgment, review, or continuation of a planning conversation — Codex handles implementation
- Do not write Execution Prompts that say "figure out the best approach" — be specific
- Do not create milestones with more than 8–10 tasks — split into smaller milestones if needed
- Do not leave the `claude.md` Architecture section empty — even a rough description of the intended structure helps Codex stay coherent across tasks

---

## Example: what a complete task looks like in Notion

```
Task:             M2-003 Implement JWT validator
Status:           Todo
Assigned Agent:   Codex
Milestone:        M2
Priority:         High
Dependencies:     M2-001 (defines TokenPayload type), M1-002 (installs jose)

Execution Prompt:
  Create the file src/auth/validator.ts.

  Requirements:
  - Export a named function validateToken(token: string): Promise<TokenPayload | null>
  - Import TokenPayload from src/types/auth.ts
  - Use the jose library's jwtVerify function
  - Read JWT_SECRET from process.env.JWT_SECRET — throw an Error at module load
    time if it is not set
  - Return null when the token is expired, malformed, or has an invalid signature
  - Do not throw on invalid tokens — only throw on missing configuration

  Constraints:
  - No default exports
  - No any types
  - No imports from src/api/ (prevents circular dependencies)

Repo Path:        src/auth/validator.ts
Notes:            (empty — orchestrator writes here on failure)
```
