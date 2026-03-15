# claude.md - Canonical Project Memory
# Workflow Analyzer - Jira Cloud Forge Application

> This is the single source of truth for the project.
> Claude updates this file after every planning step, architectural decision, or milestone change.
> Codex reads this file first before doing anything else.

---

## Project

**Name:** Workflow Analyzer  
**Platform:** Atlassian Forge (Jira Cloud)  
**Type:** Forge Custom UI App  
**Language:** TypeScript + React  
**Storage:** Forge Storage API (key-value, ~10MB limit)  
**Data Source:** Jira Cloud REST API v3  
**Repo:** `C:\ClaudeWorkspace\JIRA_workflow_project\workflow-analyzer\`
**App Root:** `workflow-analyzer/` (this directory)

---

## Mission

Build a Jira Cloud Forge application that analyzes Jira workflows and produces actionable insights about workflow complexity, health, and process quality using deterministic graph algorithms only. No external AI services. No external databases. Fully self-contained on the Atlassian Forge platform.

---

## Current Goal

**Phase:** Implementation in progress  
**Active Milestone:** M2 - Workflow API Integration  
**Blocking Issues:** None active for local repository work  
**First Task:** M2-001  
**Latest Validation:** M1-004 executed on 2026-03-15; `workflow-analyzer/` already matched the required ESLint/Prettier setup, `npm install -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser prettier eslint-config-prettier` completed with packages up to date, and `npm run lint` passed

---

## Architecture Snapshot

- Frontend: Forge Custom UI React app under `src/ui/`, bundled into `static/main/`
- Backend: Forge resolver entry points under `src/resolvers/`
- Shared contracts: TypeScript domain types under `src/types/`
- Analysis engine: Pure graph algorithms under `src/algorithms/`
- Data flow: Browser -> `invoke()` -> Forge function -> Jira API / Forge Storage -> UI render

---

## Repository Layout

```text
C:\ClaudeWorkspace\JIRA_workflow_project\workflow-analyzer\   ← REPO_PATH
|-- claude.md
|-- rolling_handoff.md
|-- task_plan.md
|-- architecture.md
|-- data_model.md
|-- analysis_algorithms.md
|-- repo_structure.md
|-- implementation_rules.md
|-- vision.md
|-- manifest.yml
|-- package.json
|-- tsconfig.json
|-- src\
|   |-- resolvers\
|   |-- algorithms\
|   |-- ui\
|   `-- types\
`-- static\
```

---

## Progress Status

| Milestone | Name | Status | Owner |
|-----------|------|--------|-------|
| M0 | Architecture & Planning | Complete | Claude |
| M1 | Forge App Scaffolding | Complete | Codex |
| M2 | Workflow API Integration | In Progress | Codex |
| M3 | Domain Model & Types | Todo | Codex |
| M4 | Analysis Engine | Todo | Codex |
| M5 | Admin Dashboard UI | Todo | Codex |
| M6 | Graph Visualization | Todo | Codex |
| M7 | Workflow Drift Comparison | Todo | Codex |
| M8 | Caching and Refresh | Todo | Codex |
| M9 | Export / Report | Todo | Codex |

---

## Current Milestone: M2 - Workflow API Integration

**Goal:** Implement typed Jira workflow retrieval, normalization, and cache-aware resolver plumbing on top of the completed Forge scaffold.

**Success criteria:**
- Jira workflow list fetches are paginated correctly
- Jira workflow detail fetch is implemented
- Jira responses are normalized into the shared domain model
- Storage helpers support cache reads and writes
- Resolver entry points compose fetch, normalize, and cache logic without TypeScript or lint errors

---

## Immediate Next Tasks for Codex

1. **M2-001** - Implement paginated workflow fetch in `src/resolvers/workflows.ts`
2. **M2-002** - Implement workflow detail fetch in `src/resolvers/workflows.ts`
3. **M2-003** - Implement Jira API response normalizer in `src/resolvers/normalizer.ts`
4. **M2-004** - Implement Forge Storage wrappers in `src/resolvers/storage.ts`
5. **M2-005** - Wire up `listWorkflows` resolver with cache

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI framework | Forge Custom UI, not UI Kit 2 | D3-based graph visualization requires Custom UI |
| Routing | Hash routing (`#/route`) | Forge iframes do not support History API navigation reliably |
| Graph structure | Adjacency list | Efficient for sparse workflow graphs |
| Drift matching | Match by status name, not ID | Names are stable across workflow copies |
| State management | Context + `useReducer` | Adequate complexity without Redux |
| Lint baseline | Extend `plugin:@typescript-eslint/recommended` and `prettier`; forbid explicit `any` | Confirmed locally on 2026-03-15 by checking `.eslintrc.js` and `.prettierrc`, re-running the exact M1-004 install command, and verifying `npm run lint`; avoids formatter conflicts |
| Persistence | Forge Storage | Native, authenticated, and sufficient for the app |
| Shortest path | BFS | Unweighted workflow graph |
| Longest path | DFS with backtracking | Workflow graphs are small enough for exhaustive traversal |
| Notion Status field | `SELECT` | Compatible with the available query tooling |
| Analysis approach | Deterministic algorithms only | Auditable and self-contained |
| UI build output | Author UI in `src/ui/`, emit bundle to `static/main/` | Keeps authored source separated from Forge static assets |

---

## Open Issues

- `npm install` reports 5 known vulnerabilities in the current dependency tree inside `workflow-analyzer/`; the 2026-03-15 M1-004 execution left remediation out of scope
- Confirm Forge Storage behavior when total analysis data exceeds ~10MB on large Jira instances
- Confirm Jira workflow search pagination behavior when `total=0` or a single page contains the full result
- Finalize health grade color palette
- Confirm Forge deployment behavior from this repository in non-TTY environments if a fresh bootstrap or deploy path is needed again

---

## State Drift Rule

**Repository files are the authoritative truth.**

If Notion tasks, repository docs, and implemented code disagree:

1. Trust the code for what has actually been built.
2. Trust repository docs for what should be built next.
3. Treat Notion as a mirror of repository docs and update it to match.

When Codex discovers a discrepancy:
- Update the affected doc file to reflect actual state
- Update the Notion task to match
- Add a note to `rolling_handoff.md` under Architecture Decisions Log

---

## Codex Entry Procedure

1. Read `claude.md`.
2. Read `rolling_handoff.md`.
3. Query the Notion database for Codex-assigned Todo tasks.
4. Select the first task whose dependencies are done.
5. Execute the task and run the required verification.
6. Update repository docs and Notion before finishing.

---

## Instructions for Codex - Hard Rules

- Never install `openai`, `anthropic`, `langchain`, or any AI/ML package
- Never put business logic inside React components
- Never call `requestJira()` from the UI layer
- Never use `any` in TypeScript; use `unknown` plus narrowing
- Never use History API routing; use hash routing
- Never start a task whose dependencies are unresolved
- Never use Redux; use Context plus `useReducer`
- Never import D3 outside `src/ui/components/WorkflowGraph.tsx`
- Never put Forge imports in `src/algorithms/`
