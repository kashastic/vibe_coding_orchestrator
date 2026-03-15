# task_plan.md — Full Task Breakdown
# Workflow Analyzer — Jira Cloud Forge Application

> This is the canonical task list.
> All tasks are also stored in Notion database: "Workflow Analyzer Build"
> Codex queries Notion for task assignments.
> Claude updates this file when tasks change or milestones progress.

---

## Milestone Overview

| ID | Milestone | Task Count | Assigned |
|----|-----------|-----------|---------|
| M0 | Architecture & Planning | 11 | Claude |
| M1 | Forge App Scaffolding | 6 | Codex |
| M2 | Workflow API Integration | 5 | Codex |
| M3 | Domain Model & Types | 3 | Codex |
| M4 | Analysis Engine | 14 | Codex |
| M5 | Admin Dashboard UI | 6 | Codex |
| M6 | Graph Visualization | 4 | Codex |
| M7 | Workflow Drift Comparison | 4 | Codex |
| M8 | Caching and Refresh | 3 | Codex |
| M9 | Export / Report | 4 | Codex |

---

## M0 — Architecture & Planning (Claude)

| ID | Task | Priority | Status |
|----|------|----------|--------|
| M0-001 | Design system architecture | High | Done |
| M0-002 | Define data model (TypeScript types) | High | Done |
| M0-003 | Specify analysis algorithms (pseudocode) | High | Done |
| M0-004 | Create claude.md | High | Done |
| M0-005 | Create architecture.md | High | Done |
| M0-006 | Create data_model.md | High | Done |
| M0-007 | Create analysis_algorithms.md | High | Done |
| M0-008 | Create task_plan.md and populate Notion | High | Done |
| M0-009 | Create repo_structure.md | High | Done |
| M0-010 | Create implementation_rules.md | High | Done |
| M0-011 | Create rolling_handoff.md | High | Done |

---

## M1 — Forge App Scaffolding (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M1-001 | Initialize Forge app with Custom UI template | High | M0 complete |
| M1-002 | Configure manifest.yml with admin page module and scopes | High | M1-001 |
| M1-003 | Set up TypeScript config (tsconfig.json, strict mode) | High | M1-001 |
| M1-004 | Set up ESLint + Prettier | Medium | M1-001 |
| M1-005 | Create base resolver entry point (src/resolvers/index.ts) | High | M1-002, M1-003 |
| M1-006 | Create base React UI shell (src/ui/App.tsx with routing skeleton) | High | M1-003 |

---

## M2 — Workflow API Integration (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M2-001 | Implement paginated workflow fetch (src/resolvers/workflows.ts) | High | M1-005 |
| M2-002 | Implement workflow detail fetch (single workflow by ID) | High | M2-001 |
| M2-003 | Implement Jira API response normalizer (src/resolvers/normalizer.ts) | High | M2-001 |
| M2-004 | Implement Forge Storage wrappers (src/resolvers/storage.ts) | High | M1-005 |
| M2-005 | Wire up listWorkflows resolver with cache | High | M2-001, M2-003, M2-004 |

---

## M3 — Domain Model Implementation (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M3-001 | Implement all TypeScript types from data_model.md (src/types/index.ts) | High | M1-003 |
| M3-002 | Implement graph builder: buildGraph() (src/algorithms/graph.ts) | High | M3-001 |
| M3-003 | Write graph builder tests (src/algorithms/__tests__/graph.test.ts) | High | M3-002 |

---

## M4 — Analysis Engine (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M4-001 | Implement complexityScore() (src/algorithms/complexity.ts) | High | M3-002 |
| M4-002 | Write complexity tests | High | M4-001 |
| M4-003 | Implement detectDeadStates() (src/algorithms/deadState.ts) | High | M3-002 |
| M4-004 | Write dead state tests | High | M4-003 |
| M4-005 | Implement detectCycles() (src/algorithms/cycles.ts) | High | M3-002 |
| M4-006 | Write cycle detection tests | High | M4-005 |
| M4-007 | Implement analyzePathLengths() (src/algorithms/pathLength.ts) | High | M3-002 |
| M4-008 | Write path length tests | High | M4-007 |
| M4-009 | Implement computeHealthScore() (src/algorithms/health.ts) | High | M4-001, M4-003, M4-005, M4-007 |
| M4-010 | Write health score tests | High | M4-009 |
| M4-011 | Implement analysis orchestrator (src/resolvers/analysis.ts) | High | M4-009, M3-002 |
| M4-012 | Wire up getWorkflowAnalysis resolver | High | M4-011, M2-005 |
| M4-013 | Wire up getHealthDashboard resolver | High | M4-012 |
| M4-014 | Integration test: full analysis pipeline on sample workflow data | Medium | M4-013 |

---

## M5 — Admin Dashboard UI (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M5-001 | Implement AppContext with useReducer (src/ui/context/AppContext.tsx) | High | M1-006 |
| M5-002 | Implement ScoreBadge component | High | M5-001 |
| M5-003 | Implement WorkflowCard component | High | M5-002 |
| M5-004 | Implement Dashboard page (src/ui/pages/Dashboard.tsx) | High | M5-003, M4-013 |
| M5-005 | Implement WorkflowDetail page (src/ui/pages/WorkflowDetail.tsx) | High | M5-002, M4-012 |
| M5-006 | Implement HealthReport page with DebtList (src/ui/pages/HealthReport.tsx) | Medium | M5-005 |

---

## M6 — Graph Visualization (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M6-001 | Install and configure D3.js | High | M1-001 |
| M6-002 | Implement WorkflowGraph D3 component (src/ui/components/WorkflowGraph.tsx) | High | M6-001, M3-002 |
| M6-003 | Implement GraphView page (src/ui/pages/GraphView.tsx) | High | M6-002 |
| M6-004 | Add visual highlights: dead states (red), cycles (orange), initial (green border) | Medium | M6-003 |

---

## M7 — Workflow Drift Comparison (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M7-001 | Implement compareWorkflows() algorithm (src/algorithms/drift.ts) | High | M3-002 |
| M7-002 | Write drift comparison tests | High | M7-001 |
| M7-003 | Wire up compareWorkflows resolver (src/resolvers/index.ts) | High | M7-001, M2-004 |
| M7-004 | Implement DriftComparison page (src/ui/pages/DriftComparison.tsx) | High | M7-003, M5-001 |

---

## M8 — Caching and Refresh (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M8-001 | Implement cache TTL check and staleness detection (storage.ts) | High | M2-004 |
| M8-002 | Implement refreshCache resolver (clears all keys, re-fetches, re-analyzes) | High | M8-001, M4-013 |
| M8-003 | Add Refresh button to Dashboard UI with loading state | Medium | M8-002, M5-004 |

---

## M9 — Export / Report (Codex)

| ID | Task | Priority | Depends On |
|----|------|----------|-----------|
| M9-001 | Implement JSON export of workflow analysis results | Low | M4-013 |
| M9-002 | Implement CSV export of health dashboard summary | Low | M4-013 |
| M9-003 | Add export buttons to Dashboard and HealthReport pages | Low | M9-001, M9-002 |
| M9-004 | Implement browser-side PDF generation of health report (using window.print CSS) | Low | M9-003 |

---

## Dependency Graph (Critical Path)

```
M0 → M1-001 → M1-002 → M1-005 → M2-001 → M2-003 → M2-005
                                          → M2-002
                         M2-004 ─────────────────────────────┐
M1-003 → M3-001 → M3-002 → M4-001 → M4-009 → M4-011 → M4-012 → M4-013
                          → M4-003 ─────────────────────────┘
                          → M4-005
                          → M4-007
M1-006 → M5-001 → M5-002 → M5-003 → M5-004 (needs M4-013)
                                   → M5-005 (needs M4-012)
M1-001 → M6-001 → M6-002 (also needs M3-002) → M6-003 → M6-004
M3-002 → M7-001 → M7-003 → M7-004 (needs M5-001)
M2-004 → M8-001 → M8-002 → M8-003 (needs M5-004)
M4-013 → M9-001, M9-002 → M9-003 → M9-004
```

---

## Notion Task Entry Template

Each task in Notion has these fields:
```
Task:            [M#-### — Task Title]
Milestone:       [M# — Milestone Name]
Status:          Todo
Assigned Agent:  Codex (or Claude)
Priority:        High / Medium / Low
Execution Prompt: [Detailed implementation instructions for Codex]
Repo Path:       [Primary file to create or modify]
Dependencies:    [Notion relations to prerequisite tasks]
Notes:           [Additional context or edge cases]
```
