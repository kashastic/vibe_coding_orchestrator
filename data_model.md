# data_model.md — TypeScript Data Model
# Workflow Analyzer — Jira Cloud Forge Application

> All types defined here must be implemented in `workflow-analyzer/src/types/index.ts`

---

## Jira API Response Types

These match the Jira Cloud REST API v3 response shapes.

```typescript
// Raw Jira workflow from GET /rest/api/3/workflow/search
interface JiraWorkflowRaw {
  id: {
    name: string;
    entityId?: string;
  };
  description?: string;
  transitions: JiraTransitionRaw[];
  statuses: JiraWorkflowStatusRaw[];
  isDefault?: boolean;
  created?: string;
  updated?: string;
}

interface JiraTransitionRaw {
  id: string;
  name: string;
  type: 'initial' | 'global' | 'directed';
  from?: string[];   // source status IDs (empty = initial transition)
  to: string;        // destination status ID
  conditions?: JiraConditionRaw[];
  validators?: JiraValidatorRaw[];
  postFunctions?: JiraPostFunctionRaw[];
}

interface JiraWorkflowStatusRaw {
  id: string;
  name: string;
  statusCategory: {
    id: number;
    key: 'new' | 'indeterminate' | 'done' | 'undefined';
    colorName: string;
    name: string;
  };
  properties?: Record<string, string>;
}

interface JiraConditionRaw {
  type: string;
  configuration?: Record<string, unknown>;
}

interface JiraValidatorRaw {
  type: string;
  configuration?: Record<string, unknown>;
}

interface JiraPostFunctionRaw {
  type: string;
  configuration?: Record<string, unknown>;
}

// Paginated response from /rest/api/3/workflow/search
interface JiraWorkflowSearchResponse {
  values: JiraWorkflowRaw[];
  startAt: number;
  maxResults: number;
  total: number;
  isLast: boolean;
}
```

---

## Domain Model

These are the normalized, internal representations used by the analysis engine.

```typescript
// Normalized workflow status (node in workflow graph)
interface WorkflowStatus {
  id: string;
  name: string;
  category: 'todo' | 'in_progress' | 'done' | 'unknown';
  isInitial: boolean;
  isTerminal: boolean;    // category === 'done'
}

// Normalized transition (directed edge in workflow graph)
interface WorkflowTransition {
  id: string;
  name: string;
  fromStatusId: string | null;  // null = initial transition (no source)
  toStatusId: string;
  type: 'initial' | 'global' | 'directed';
  hasConditions: boolean;
  hasValidators: boolean;
  hasPostFunctions: boolean;
  conditionCount: number;
  validatorCount: number;
  postFunctionCount: number;
}

// Summary card — used in list views, stored in workflows_list cache
interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  isDefault: boolean;
  statusCount: number;
  transitionCount: number;
  lastUpdated: string;   // ISO timestamp
  healthScore?: number;  // 0–100, populated after analysis
  complexityScore?: number;
}

// Full workflow detail — stored per workflow in cache
interface WorkflowDetail {
  id: string;
  name: string;
  description: string;
  isDefault: boolean;
  statuses: WorkflowStatus[];
  transitions: WorkflowTransition[];
  lastUpdated: string;
  cachedAt: string;      // ISO timestamp of when we cached it
}
```

---

## Graph Model

```typescript
// Directed graph represented as adjacency list
// Nodes = statuses, Edges = transitions
interface WorkflowGraph {
  nodes: Map<string, WorkflowStatus>;          // statusId → status
  edges: Map<string, WorkflowTransition[]>;    // fromStatusId → transitions
  incomingEdges: Map<string, WorkflowTransition[]>;  // toStatusId → transitions
  initialStatusId: string | null;
  terminalStatusIds: Set<string>;
}

// Helper type for graph traversal
interface GraphNode {
  id: string;
  outgoing: string[];   // target status IDs
  incoming: string[];   // source status IDs
}
```

---

## Analysis Result Types

```typescript
// Complexity scoring result
interface ComplexityResult {
  score: number;         // 0–100 (higher = more complex)
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  breakdown: {
    statusCount: number;
    transitionCount: number;
    globalTransitionCount: number;
    avgOutdegree: number;
    maxOutdegree: number;
    conditionDensity: number;   // avg conditions per transition
    branchingFactor: number;    // transitions / statuses ratio
  };
}

// Dead state = status with no outgoing path to any terminal status
interface DeadState {
  statusId: string;
  statusName: string;
  reason: 'no_outgoing_transitions' | 'no_path_to_terminal';
  reachableFrom: string[];   // status IDs that can reach this dead state
}

// A cycle detected in the workflow graph
interface Cycle {
  statusIds: string[];        // ordered list of status IDs forming the cycle
  statusNames: string[];      // human-readable names
  length: number;             // number of statuses in cycle
  transitionNames: string[];  // transition names traversed
}

// Path length analysis
interface PathAnalysis {
  shortestPathToTerminal: number;   // min hops from initial to any terminal
  longestPathToTerminal: number;    // max hops (simple path, no cycles)
  averagePathLength: number;
  unreachableStatuses: string[];    // status IDs not reachable from initial
  pathDetails: PathDetail[];
}

interface PathDetail {
  fromStatusId: string;
  toStatusId: string;
  hopCount: number;
  path: string[];   // sequence of status IDs
}

// Health / technical debt score
interface HealthScore {
  overall: number;       // 0–100 (higher = healthier)
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  debtItems: DebtItem[];
  breakdown: {
    complexityPenalty: number;
    deadStatePenalty: number;
    cyclePenalty: number;
    pathLengthPenalty: number;
    unreachablePenalty: number;
  };
}

interface DebtItem {
  severity: 'critical' | 'warning' | 'info';
  category: 'dead_state' | 'cycle' | 'complexity' | 'unreachable' | 'long_path';
  message: string;
  affectedIds: string[];   // status or transition IDs
}

// Complete analysis result for one workflow
interface WorkflowAnalysis {
  workflowId: string;
  workflowName: string;
  graph: SerializedGraph;     // serializable version for storage
  complexity: ComplexityResult;
  deadStates: DeadState[];
  cycles: Cycle[];
  paths: PathAnalysis;
  health: HealthScore;
  analyzedAt: string;         // ISO timestamp
}

// Serializable graph (Maps → Records for JSON storage)
interface SerializedGraph {
  nodes: Record<string, WorkflowStatus>;
  edges: Record<string, WorkflowTransition[]>;
  initialStatusId: string | null;
  terminalStatusIds: string[];
}
```

---

## Drift Comparison Types

```typescript
// Result of comparing two workflows
interface DriftResult {
  workflowA: WorkflowSummary;
  workflowB: WorkflowSummary;
  driftScore: number;        // 0–100 (higher = more different)
  addedStatuses: WorkflowStatus[];      // in B, not in A
  removedStatuses: WorkflowStatus[];    // in A, not in B
  addedTransitions: WorkflowTransition[];
  removedTransitions: WorkflowTransition[];
  changedTransitions: TransitionChange[];
  commonStatuses: WorkflowStatus[];
  commonTransitions: WorkflowTransition[];
}

interface TransitionChange {
  transitionId: string;
  transitionName: string;
  changes: {
    field: string;
    valueBefore: unknown;
    valueAfter: unknown;
  }[];
}
```

---

## Dashboard Types

```typescript
// Top-level dashboard data (cached as health_dashboard)
interface HealthDashboard {
  totalWorkflows: number;
  analyzedAt: string;
  averageHealthScore: number;
  averageComplexityScore: number;
  workflowSummaries: WorkflowDashboardRow[];
  systemAlerts: DebtItem[];    // critical items across all workflows
}

interface WorkflowDashboardRow {
  id: string;
  name: string;
  healthScore: number;
  healthGrade: 'A' | 'B' | 'C' | 'D' | 'F';
  complexityScore: number;
  complexityGrade: 'A' | 'B' | 'C' | 'D' | 'F';
  deadStateCount: number;
  cycleCount: number;
  statusCount: number;
  transitionCount: number;
  isDefault: boolean;
}
```

---

## Forge Resolver Request/Response Types

```typescript
// Resolver function signatures (used in resolvers/index.ts)

// getHealthDashboard
type GetHealthDashboardRequest = Record<string, never>;
type GetHealthDashboardResponse = HealthDashboard;

// getWorkflowAnalysis
interface GetWorkflowAnalysisRequest {
  workflowId: string;
}
type GetWorkflowAnalysisResponse = WorkflowAnalysis;

// compareWorkflows
interface CompareWorkflowsRequest {
  workflowIdA: string;
  workflowIdB: string;
}
type CompareWorkflowsResponse = DriftResult;

// refreshCache
type RefreshCacheRequest = Record<string, never>;
interface RefreshCacheResponse {
  success: boolean;
  workflowsRefreshed: number;
  refreshedAt: string;
}

// listWorkflows
type ListWorkflowsRequest = Record<string, never>;
type ListWorkflowsResponse = WorkflowSummary[];
```
