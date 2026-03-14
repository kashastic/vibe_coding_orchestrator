# architecture.md — System Architecture
# Workflow Analyzer — Jira Cloud Forge Application

---

## Overview

Workflow Analyzer is a Jira Cloud Forge application delivered as a **Custom UI** app (React frontend + Forge backend functions). It reads Jira workflows via the Jira REST API, runs deterministic graph analysis, caches results in Forge Storage, and presents insights via an admin dashboard.

---

## Platform: Atlassian Forge

Forge is Atlassian's serverless cloud development platform. Key constraints:

| Constraint | Value |
|------------|-------|
| Execution model | Serverless functions (Node.js runtime) |
| Frontend | Custom UI via iframe (full React app) |
| Storage | Forge Storage (key-value, ~10MB/app) |
| Auth | Automatic OAuth via Forge (no tokens to manage) |
| API calls | Via `@forge/api` `requestJira()` — no CORS issues |
| Deployment | `forge deploy` to Atlassian cloud |
| Scopes | Declared in manifest.yml |

---

## Component Map

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (Jira Admin Page)                                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Custom UI iframe                                              │  │
│  │                                                                │  │
│  │  React App (TypeScript)                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐  │  │
│  │  │ Dashboard  │  │  Detail    │  │  Graph     │  │  Drift  │  │  │
│  │  │   Page     │  │   Page     │  │   View     │  │  View   │  │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬────┘  │  │
│  │        └───────────────┴───────────────┴──────────────┘        │  │
│  │                              │                                  │  │
│  │              @forge/bridge invoke()                             │  │
│  └──────────────────────────────┼──────────────────────────────────┘  │
│                                 │                                    │
└─────────────────────────────────┼────────────────────────────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │   Forge Functions (Node.js)   │
                    │                              │
                    │  resolvers/index.ts          │
                    │  ┌────────────────────────┐  │
                    │  │  fetchWorkflows        │  │
                    │  │  getWorkflowAnalysis   │  │
                    │  │  compareWorkflows      │  │
                    │  │  getHealthDashboard    │  │
                    │  │  refreshCache          │  │
                    │  └──────────┬─────────────┘  │
                    │             │                 │
                    └─────────────┼─────────────────┘
                                  │
               ┌──────────────────┴──────────────────┐
               │                                      │
   ┌───────────▼──────────┐            ┌─────────────▼──────────┐
   │   Jira REST API v3    │            │    Forge Storage        │
   │                      │            │                        │
   │  GET /workflow/search │            │  workflows:{id}        │
   │  GET /statuses        │            │  analysis:{id}         │
   │  GET /workflowscheme  │            │  health_dashboard       │
   │  GET /issuetype       │            │  last_refresh          │
   └──────────────────────┘            └────────────────────────┘
```

---

## Data Flow

### 1. Initial Load (Dashboard)

```
Browser → invoke("getHealthDashboard")
  → Check Forge Storage for cached dashboard
  → If cache miss or stale (>1hr):
      → requestJira GET /workflow/search (paginated)
      → For each workflow: run all analysis algorithms
      → Store results in Forge Storage
      → Return dashboard summary
  → Return cached dashboard summary
```

### 2. Workflow Detail View

```
Browser → invoke("getWorkflowAnalysis", { workflowId })
  → Check Forge Storage for workflow analysis
  → If miss: fetch single workflow, run analysis, store
  → Return: { graph, complexityScore, deadStates, cycles, paths, healthScore }
```

### 3. Drift Comparison

```
Browser → invoke("compareWorkflows", { workflowIdA, workflowIdB })
  → Fetch/load both workflow analyses
  → Run drift algorithm: diff states and transitions
  → Return: { added, removed, changed, driftScore }
```

### 4. Cache Refresh

```
Browser → invoke("refreshCache")
  → Clear all Forge Storage entries
  → Re-fetch all workflows
  → Re-run all analysis
  → Update storage
```

---

## Forge Manifest Modules

```yaml
# manifest.yml (summary)
modules:
  jira:adminPage:
    - key: workflow-analyzer-admin
      resource: main
      resolver:
        function: resolver
      title: Workflow Analyzer

  function:
    - key: resolver
      handler: src/resolvers/index.handler

resources:
  - key: main
    path: static/main
    tunnel:
      port: 3000

permissions:
  scopes:
    - read:jira-work
    - read:jira-user
    - manage:jira-configuration   # needed for workflow read
```

---

## Forge Storage Schema

All keys stored in Forge Storage under app context:

| Key Pattern | Value | TTL Strategy |
|-------------|-------|-------------|
| `workflows_list` | `WorkflowSummary[]` | Refresh on demand |
| `workflow:{id}` | `WorkflowDetail` | Refresh on demand |
| `analysis:{id}` | `WorkflowAnalysis` | Refresh on demand |
| `health_dashboard` | `HealthDashboard` | Refresh on demand |
| `last_refresh` | ISO timestamp string | Always updated |

---

## Analysis Engine Architecture

The analysis engine is a pure TypeScript module with no side effects. It takes a workflow graph and returns structured results.

```
WorkflowGraph (adjacency list)
    │
    ├── complexityScore(graph)    → ComplexityResult
    ├── detectDeadStates(graph)   → DeadState[]
    ├── detectCycles(graph)       → Cycle[]
    ├── analyzePathLengths(graph) → PathAnalysis
    └── computeHealthScore(       → HealthScore
            ComplexityResult,
            DeadState[],
            Cycle[],
            PathAnalysis
        )
```

All algorithms are O(V + E) or O(V²) worst case. Workflows are small graphs (typically 5–30 nodes), so performance is not a concern.

---

## Frontend Architecture

React SPA served as Forge Custom UI. Uses `@forge/bridge` for all backend communication.

```
App.tsx
├── Router (hash-based, no server routing)
├── pages/
│   ├── Dashboard.tsx       — health overview, all workflows
│   ├── WorkflowDetail.tsx  — single workflow analysis
│   ├── GraphView.tsx       — D3.js graph visualization
│   ├── DriftComparison.tsx — side-by-side drift view
│   └── HealthReport.tsx    — technical debt detail
└── components/
    ├── WorkflowCard.tsx    — summary card per workflow
    ├── ScoreBadge.tsx      — color-coded score badge
    ├── WorkflowGraph.tsx   — D3 graph wrapper component
    └── MetricsTable.tsx    — tabular metrics display
```

State management: React Context + useReducer (no Redux — overkill for this app).

---

## API Scopes Required

| Scope | Purpose |
|-------|---------|
| `read:jira-work` | Read issue types, projects |
| `manage:jira-configuration` | Read workflow definitions |

---

## Security Model

- Forge platform handles all authentication (no tokens stored)
- `requestJira()` runs server-side — no Jira credentials exposed to browser
- All analysis runs server-side in Forge functions
- Forge Storage is isolated per app instance
- No user data stored — only workflow metadata and analysis results

---

## Deployment Environments

| Environment | Command | Purpose |
|-------------|---------|---------|
| Development | `forge deploy --environment development` | Dev/test |
| Staging | `forge deploy --environment staging` | Pre-prod |
| Production | `forge deploy --environment production` | Live |
| Local tunnel | `forge tunnel` | Local dev with hot reload |
