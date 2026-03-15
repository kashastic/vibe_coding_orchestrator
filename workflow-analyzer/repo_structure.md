# repo_structure.md — Repository File Structure
# Workflow Analyzer — Jira Cloud Forge Application

> This file defines the canonical repository structure.
> Codex must follow this exactly.
> If a new file is needed, add it here first, then create it.

---

## Root Level (Project Planning)

```
/
├── claude.md                  ← Canonical project memory (always read first)
├── architecture.md            ← System architecture and design
├── data_model.md              ← TypeScript types and interfaces
├── analysis_algorithms.md     ← Algorithm pseudocode specifications
├── repo_structure.md          ← This file
├── implementation_rules.md    ← Coding standards for Codex
├── task_plan.md               ← Full task list with dependencies
└── rolling_handoff.md         ← Latest state and handoff notes
```

---

## Forge Application (Created by Codex in M1)

```
workflow-analyzer/
│
├── manifest.yml               ← Forge app manifest (modules, permissions, resources)
├── package.json               ← Node.js dependencies and scripts
├── package-lock.json          ← Locked dependency tree
├── tsconfig.json              ← TypeScript config (strict mode)
├── .eslintrc.js               ← ESLint config
├── .prettierrc                ← Prettier config
├── forge.config.js            ← Forge-specific build config (if needed)
│
├── src/
│   │
│   ├── resolvers/
│   │   ├── index.ts           ← Forge resolver entry point (exports handler)
│   │   ├── workflows.ts       ← fetchWorkflows, fetchWorkflowDetail, paginator
│   │   ├── analysis.ts        ← analyzeWorkflow orchestrator (calls algorithms)
│   │   ├── storage.ts         ← Forge Storage CRUD wrappers + cache logic
│   │   └── normalizer.ts      ← Maps Jira API response → domain model types
│   │
│   ├── algorithms/
│   │   ├── graph.ts           ← buildGraph(), serialization helpers, clamp/grade
│   │   ├── complexity.ts      ← computeComplexity()
│   │   ├── deadState.ts       ← detectDeadStates()
│   │   ├── cycles.ts          ← detectCycles()
│   │   ├── pathLength.ts      ← analyzePathLengths()
│   │   ├── drift.ts           ← compareWorkflows()
│   │   ├── health.ts          ← computeHealthScore()
│   │   └── __tests__/
│   │       ├── graph.test.ts
│   │       ├── complexity.test.ts
│   │       ├── deadState.test.ts
│   │       ├── cycles.test.ts
│   │       ├── pathLength.test.ts
│   │       ├── drift.test.ts
│   │       └── health.test.ts
│   │
│   ├── ui/
│   │   ├── index.tsx          ← React entry point (renders <App />)
│   │   ├── App.tsx            ← Root component with Router and Context providers
│   │   ├── context/
│   │   │   └── AppContext.tsx ← Global state: currentWorkflow, dashboard, loading
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      ← Main admin page (health overview of all workflows)
│   │   │   ├── WorkflowDetail.tsx ← Single workflow analysis view
│   │   │   ├── GraphView.tsx      ← Full-page D3 graph visualization
│   │   │   ├── DriftComparison.tsx← Side-by-side workflow comparison
│   │   │   └── HealthReport.tsx   ← Technical debt detail view
│   │   └── components/
│   │       ├── WorkflowCard.tsx   ← Summary card for one workflow
│   │       ├── ScoreBadge.tsx     ← Color-coded score + grade badge
│   │       ├── WorkflowGraph.tsx  ← D3.js graph wrapper (SVG-based)
│   │       ├── MetricsTable.tsx   ← Tabular display of analysis metrics
│   │       ├── DebtList.tsx       ← List of technical debt items
│   │       ├── CycleList.tsx      ← List of detected cycles
│   │       ├── DriftSummary.tsx   ← Summary of drift between two workflows
│   │       ├── LoadingState.tsx   ← Spinner + message
│   │       └── ErrorState.tsx     ← Error display with retry button
│   │
│   └── types/
│       └── index.ts           ← ALL shared TypeScript types (from data_model.md)
│
└── static/
    └── main/                  ← Forge Custom UI static output (built by webpack/vite)
        └── (auto-generated — do not edit manually)
```

---

## Key File Responsibilities

### `manifest.yml`
```yaml
# Must declare:
# - jira:adminPage module pointing to static/main resource
# - resolver function pointing to src/resolvers/index.handler
# - permissions: read:jira-work, manage:jira-configuration
```

### `src/resolvers/index.ts`
```typescript
// Must export: handler
// Must define resolvers:
//   - getHealthDashboard
//   - listWorkflows
//   - getWorkflowAnalysis
//   - compareWorkflows
//   - refreshCache
```

### `src/types/index.ts`
```typescript
// Must contain ALL types from data_model.md
// This is the single source of type truth
// Both resolvers/ and ui/ import from here
```

### `src/ui/App.tsx`
```typescript
// Must provide:
//   - Hash-based routing (#/dashboard, #/workflow/:id, #/graph/:id, #/drift, #/health/:id)
//   - AppContext provider wrapping all pages
//   - Global navigation header
```

---

## Build Scripts (package.json)

```json
{
  "scripts": {
    "build": "webpack --config webpack.config.js",
    "start": "webpack serve --config webpack.config.js",
    "lint": "eslint src --ext .ts,.tsx",
    "test": "jest",
    "test:coverage": "jest --coverage",
    "forge:deploy": "forge deploy --environment development",
    "forge:tunnel": "forge tunnel"
  }
}
```

---

## Dependencies

### Production Dependencies
```json
{
  "@forge/api": "^2.x",
  "@forge/bridge": "^3.x",
  "@forge/resolver": "^1.x",
  "@atlaskit/button": "latest",
  "@atlaskit/spinner": "latest",
  "@atlaskit/badge": "latest",
  "@atlaskit/lozenge": "latest",
  "@atlaskit/page-layout": "latest",
  "@atlaskit/table": "latest",
  "d3": "^7.x",
  "react": "^18.x",
  "react-dom": "^18.x"
}
```

### Dev Dependencies
```json
{
  "@types/d3": "^7.x",
  "@types/react": "^18.x",
  "@types/react-dom": "^18.x",
  "@types/jest": "^29.x",
  "jest": "^29.x",
  "ts-jest": "^29.x",
  "typescript": "^5.x",
  "eslint": "^8.x",
  "@typescript-eslint/eslint-plugin": "^6.x",
  "@typescript-eslint/parser": "^6.x",
  "prettier": "^3.x",
  "webpack": "^5.x",
  "webpack-cli": "^5.x",
  "ts-loader": "^9.x"
}
```
