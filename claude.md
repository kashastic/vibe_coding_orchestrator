# claude.md — Canonical Project Memory
# Workflow Analyzer — Jira Cloud Forge Application

> This is the single source of truth for the project.
> Claude updates this file after every planning step, architectural decision, or milestone change.
> Codex reads this file FIRST before doing anything else.

---

## Project

**Name:** Workflow Analyzer
**Platform:** Atlassian Forge (Jira Cloud)
**Type:** Forge Custom UI App
**Language:** TypeScript + React
**Storage:** Forge Storage API (key-value, ~10MB limit)
**Data Source:** Jira Cloud REST API v3
**Repo:** `C:\ClaudeWorkspace\JIRA_workflow_project\`
**App Root:** `workflow-analyzer/` (created by Codex in M1-001)

---

## Mission

Build a Jira Cloud Forge application that analyzes Jira workflows and produces actionable insights about workflow complexity, health, and process quality — using deterministic graph algorithms only. No external AI services. No external databases. Fully self-contained on the Atlassian Forge platform.

---

## Current Goal

**Phase:** Orchestration complete — Codex begins implementation
**Active Milestone:** M1 — Forge App Scaffolding
**Blocking Issues:** None
**First Task:** M1-001

---

## Architecture Snapshot

```
┌──────────────────────────────────────────────────────────────┐
│                     Jira Cloud Instance                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  Forge Platform                         │  │
│  │                                                        │  │
│  │  ┌──────────────────┐    ┌───────────────────────┐    │  │
│  │  │ Custom UI (React) │    │  Forge Functions (TS) │    │  │
│  │  │                  │◄──►│                       │    │  │
│  │  │ Admin Dashboard  │    │  fetchWorkflows        │    │  │
│  │  │ Graph View       │    │  analyzeWorkflow       │    │  │
│  │  │ Drift Comparison │    │  compareWorkflows      │    │  │
│  │  │ Health Report    │    │  getHealthDashboard    │    │  │
│  │  └──────────────────┘    │  refreshCache          │    │  │
│  │                          └──────────┬─────────────┘    │  │
│  │  ┌───────────────────────────────── │ ──────────────┐  │  │
│  │  │            Forge Storage          │               │  │  │
│  │  │  workflows_list   workflow:{id}   │               │  │  │
│  │  │  analysis:{id}    health_dashboard│               │  │  │
│  │  │  last_refresh     workflow_ids    │               │  │  │
│  │  └───────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                   Jira REST API v3                            │
│             /rest/api/3/workflow/search                       │
└──────────────────────────────────────────────────────────────┘
```

**Data flow:** Browser → `invoke()` → Forge Function → Jira API / Forge Storage → return → React renders

---

## Repository Layout

```
C:\ClaudeWorkspace\JIRA_workflow_project\
│
├── claude.md                  ← YOU ARE HERE — read first
├── rolling_handoff.md         ← Current state — read second
├── architecture.md            ← System design, component map, data flow
├── data_model.md              ← All TypeScript interfaces — implement verbatim
├── analysis_algorithms.md     ← Algorithm pseudocode — implement exactly
├── repo_structure.md          ← File/folder layout for workflow-analyzer/
├── implementation_rules.md    ← 15 coding rules Codex must follow
└── task_plan.md               ← Full task list with dependency graph
│
└── workflow-analyzer/         ← Forge app root (Codex creates in M1-001)
    ├── manifest.yml
    ├── package.json
    ├── tsconfig.json
    ├── src/
    │   ├── resolvers/         ← Forge backend: API calls, storage, orchestration
    │   ├── algorithms/        ← Pure graph analysis: no Forge or Jira imports allowed
    │   ├── ui/                ← React components: no business logic allowed
    │   └── types/             ← index.ts — ALL shared TypeScript types
    └── static/                ← Built Custom UI assets (auto-generated, do not edit)
```

---

## Progress Status

| Milestone | Name | Status | Owner |
|-----------|------|--------|-------|
| M0 | Architecture & Planning | ✅ Complete | Claude |
| M1 | Forge App Scaffolding | ⬜ Next | Codex |
| M2 | Workflow API Integration | ⬜ Todo | Codex |
| M3 | Domain Model Implementation | ⬜ Todo | Codex |
| M4 | Analysis Engine | ⬜ Todo | Codex |
| M5 | Admin Dashboard UI | ⬜ Todo | Codex |
| M6 | Graph Visualization | ⬜ Todo | Codex |
| M7 | Workflow Drift Comparison | ⬜ Todo | Codex |
| M8 | Caching and Refresh | ⬜ Todo | Codex |
| M9 | Export / Report | ⬜ Todo | Codex |

---

## Current Milestone: M1 — Forge App Scaffolding

**Goal:** Bootstrap the Forge project with the correct structure, TypeScript config, ESLint, base resolver, and React UI shell. No application logic yet — a working skeleton that deploys.

**Success criteria:**
- `forge lint` passes with zero errors
- `forge deploy --environment development` succeeds
- `invoke('ping')` returns `{ pong: true }` from the browser
- Hash routing renders the correct stub page per route
- TypeScript compiles with `strict: true` and zero errors

---

## Immediate Next Tasks for Codex

1. **M1-001** — Initialize Forge app with Custom UI template ← START HERE
2. **M1-002** — Configure manifest.yml with admin page module and scopes
3. **M1-003** — Set up TypeScript config (strict mode)
4. **M1-004** — Set up ESLint + Prettier
5. **M1-005** — Create base Forge resolver entry point
6. **M1-006** — Create base React UI shell with hash routing

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI framework | Forge Custom UI (not UI Kit 2) | Need D3.js for graph visualization — UI Kit 2 cannot run D3 |
| Routing | Hash-based (`#/route`) | Forge Custom UI iframes block History API `pushState` |
| Graph structure | Adjacency list | Efficient for sparse workflow graphs (5–30 nodes) |
| Drift matching | By status name, not ID | Names are stable across workflow copies; IDs are not |
| State management | Context + useReducer | Complexity doesn't justify Redux; no extra dependency |
| Persistence | Forge Storage | Free, native, no auth overhead; sufficient for this use case |
| Shortest path | BFS | Unweighted graph; BFS is simpler and equivalent to Dijkstra |
| Longest path | DFS with backtracking | Workflow graphs are tiny — NP complexity is not a concern |
| Notion Status field | SELECT type | Notion's STATUS type is not queryable via MCP SQLite interface |
| Analysis approach | Deterministic algorithms only | Fully auditable; no external AI dependencies |

---

## Open Issues

- [ ] Confirm Forge Storage behavior when total analysis data exceeds ~10MB (large instances, 100+ workflows)
- [ ] Confirm exact Jira API pagination behavior when `total=0` or result fits in one page
- [ ] Finalize health grade color palette (proposal: A=green #36B37E, B=teal #00B8D9, C=yellow #FF991F, D=orange #FF7452, F=red #FF5630)

---

## State Drift Rule

**Repository files are the authoritative truth.**

If Notion tasks, repository docs, and implemented code ever disagree:

1. Trust the **code** for what has actually been built
2. Trust the **repository docs** (this file, rolling_handoff.md, task_plan.md) for what should be built
3. Treat Notion as a **mirror** of repository docs — update it to match, never the reverse

When Codex discovers a discrepancy:
- Update the affected doc file to reflect actual state
- Update the Notion task to match
- Add a note to rolling_handoff.md under Architecture Decisions Log

---

## Codex Entry Procedure

When Codex starts a new session, execute these steps in order:

```
1. Read claude.md
   → Understand project mission, architecture, current milestone, key decisions

2. Read rolling_handoff.md
   → Understand current state, last completed task, next tasks, any blockers

3. Query Notion database
   → Database: Workflow Analyzer Build
   → URL: https://www.notion.so/dc46b0e161714fc89ff9be036958cae9
   → Data Source ID: d60b1f5c-7c94-4026-8ec8-3da91423f53e
   → Query: WHERE "Assigned Agent" = 'Codex'
              AND ("Status" = 'Todo' OR "Status" IS NULL)
            ORDER BY "Milestone" ASC, "Priority" DESC

4. Select next task
   → Pick the first result from the query above
   → Check its Dependencies field
   → Do NOT start a task whose dependencies are not all Done

5. Execute the task
   → Follow the Execution Prompt in Notion exactly
   → Write code to the Repo Path specified
   → Follow all 15 rules in implementation_rules.md
   → Do not skip tests

6. Update repository docs
   → Set Notion task Status to Done (or Blocked with a note)
   → Update rolling_handoff.md: date, completed task, next task, any new decisions
   → If architecture changed: update claude.md Key Decisions or Open Issues
   → Return to step 3
```

---

## Instructions for Codex — Hard Rules

- **Never** install `openai`, `anthropic`, `langchain`, or any AI/ML package
- **Never** put business logic inside React components
- **Never** call `requestJira()` from the UI layer — resolvers only
- **Never** use `any` types in TypeScript — use `unknown` + type narrowing
- **Never** use History API (`pushState`) — use `window.location.hash` routing
- **Never** start a task whose dependencies are not yet Done
- **Never** use Redux — use Context + useReducer
- **Never** import D3 outside of `src/ui/components/WorkflowGraph.tsx`
- **Never** put Forge imports (`@forge/api`, `@forge/resolver`) in `src/algorithms/`
