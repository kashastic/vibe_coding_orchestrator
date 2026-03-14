# rolling_handoff.md — Rolling Handoff
# Workflow Analyzer — Jira Cloud Forge Application

> Codex reads this SECOND (after claude.md).
> Keep this file concise and current. Update it after every completed task.

---

## Last Updated

**Date:** 2026-03-14
**By:** Claude
**Action:** Final hardening pass complete. System ready for Codex.

---

## Current Milestone

**M1 — Forge App Scaffolding**
Status: Not started. M0 (planning) is complete.

---

## Last Completed Task

**M0 — Architecture & Planning (Claude)**
All planning deliverables complete:
- Architecture designed, data model defined, algorithms specified
- 49 tasks created in Notion (M1–M9), all assigned to Codex
- 8 repository documentation files created and synchronized
- Notion schema finalized: Task, Milestone, Status, Assigned Agent, Priority, Execution Prompt, Repo Path, Dependencies, Notes, Created Time, Last Edited Time

---

## Current Repo State

```
C:\ClaudeWorkspace\JIRA_workflow_project\
├── claude.md              ✅ Complete
├── rolling_handoff.md     ✅ Complete (this file)
├── architecture.md        ✅ Complete
├── data_model.md          ✅ Complete
├── analysis_algorithms.md ✅ Complete
├── repo_structure.md      ✅ Complete
├── implementation_rules.md ✅ Complete
└── task_plan.md           ✅ Complete

workflow-analyzer/         ❌ Does not exist yet — Codex creates in M1-001
```

---

## Next Three Tasks

### 1. M1-001 — Initialize Forge app (START HERE)

```
Dependencies: None
Repo Path:    workflow-analyzer/ (root)

STEPS:
  npm install -g @forge/cli
  forge login
  cd C:\ClaudeWorkspace\JIRA_workflow_project
  forge create
    → App name: workflow-analyzer
    → Template:  custom-ui   (NOT UI Kit — must be Custom UI)
  cd workflow-analyzer && npm install
  forge lint   ← must pass with zero errors

Do NOT modify files. Scaffold only.
DONE: Set Notion M1-001 Status = Done. Proceed to M1-002.
```

### 2. M1-002 — Configure manifest.yml

```
Dependencies: M1-001
Repo Path:    workflow-analyzer/manifest.yml

Edit manifest.yml:
  - Add jira:adminPage module:
      key: workflow-analyzer-admin
      resource: main
      resolver: { function: resolver }
      title: Workflow Analyzer
  - Add function:
      key: resolver
      handler: src/resolvers/index.handler
  - Add resource:
      key: main
      path: static/main
  - Add permissions.scopes:
      - read:jira-work
      - manage:jira-configuration

Run: forge lint   ← must pass.
```

### 3. M1-003 — TypeScript configuration

```
Dependencies: M1-001
Repo Path:    workflow-analyzer/tsconfig.json

Create tsconfig.json:
  compilerOptions:
    target: ES2020
    module: commonjs
    strict: true            ← mandatory
    esModuleInterop: true
    skipLibCheck: true
    jsx: react-jsx
    outDir: ./dist
    rootDir: ./src
  include: ["src"]

Install: npm install -D typescript @types/react @types/react-dom @types/node
Verify:  npx tsc --noEmit   ← must pass.
```

---

## Blockers

None.

---

## Relevant Files

| File | When to read |
|------|-------------|
| `claude.md` | Start of every session |
| `data_model.md` | Before writing any TypeScript types or interfaces |
| `analysis_algorithms.md` | Before implementing any algorithm in `src/algorithms/` |
| `implementation_rules.md` | Before writing any code at all |
| `repo_structure.md` | When creating new files — check the canonical location first |
| `architecture.md` | When making decisions about data flow or component boundaries |

---

## Notion Task Database

| Field | Value |
|-------|-------|
| Name | Workflow Analyzer Build |
| URL | https://www.notion.so/dc46b0e161714fc89ff9be036958cae9 |
| Data Source ID | d60b1f5c-7c94-4026-8ec8-3da91423f53e |

**Query for next task:**
```sql
SELECT * FROM "collection://d60b1f5c-7c94-4026-8ec8-3da91423f53e"
WHERE "Assigned Agent" = 'Codex'
  AND ("Status" = 'Todo' OR "Status" IS NULL)
ORDER BY "Milestone" ASC, "Priority" DESC
LIMIT 1
```

**Status convention:** M1 tasks have explicit `Todo` status. M2–M9 tasks have `null` Status. Treat `null` as `Todo`. Set to `Doing` when starting, `Done` when complete, `Blocked` if a dependency is unresolved.

---

## State Drift Rule

Repository files are authoritative. If Notion, docs, and code disagree:
- Trust **code** for what is built
- Trust **repo docs** for what should be built
- Update Notion to match docs — never the reverse

---

## Architecture Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-14 | Forge Custom UI not UI Kit 2 | Need D3.js for graph visualization |
| 2026-03-14 | Hash routing `#/route` | Forge iframe blocks `pushState` |
| 2026-03-14 | Drift comparison by status name | IDs differ across workflow copies |
| 2026-03-14 | Context + useReducer not Redux | Sufficient for this app's complexity |
| 2026-03-14 | SELECT type for Notion Status field | Notion STATUS type not queryable via MCP |
| 2026-03-14 | BFS reverse from terminals for dead state detection | O(V+E), correct and simple |
| 2026-03-14 | DFS three-color for cycle detection | Handles self-loops and all cycle types |
| 2026-03-14 | Store `workflow_ids` key in Forge Storage | Forge Storage has no key enumeration |
