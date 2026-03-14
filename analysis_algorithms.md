# analysis_algorithms.md — Algorithm Specifications
# Workflow Analyzer — Jira Cloud Forge Application

> All algorithms must be implemented as pure functions in `workflow-analyzer/src/algorithms/`
> No side effects. No external calls. Input → Output only.
> All types referenced here are defined in data_model.md

---

## Graph Representation

Workflows are modeled as **directed graphs**:
- **Nodes** = workflow statuses
- **Edges** = workflow transitions (directed: from → to)
- **Initial node** = status reached by the `initial` transition (no source)
- **Terminal nodes** = statuses with category `done`

Use an adjacency list for efficiency. Graph construction is O(V + E).

### Graph Builder

**File:** `src/algorithms/graph.ts`

```
FUNCTION buildGraph(detail: WorkflowDetail) → WorkflowGraph:

  nodes = new Map()
  edges = new Map()
  incomingEdges = new Map()
  initialStatusId = null
  terminalStatusIds = new Set()

  FOR EACH status IN detail.statuses:
    nodes.set(status.id, status)
    edges.set(status.id, [])
    incomingEdges.set(status.id, [])
    IF status.isTerminal:
      terminalStatusIds.add(status.id)

  FOR EACH transition IN detail.transitions:
    IF transition.type === 'initial':
      initialStatusId = transition.toStatusId
      // initial transitions have no source — skip edge creation
    ELSE IF transition.type === 'global':
      // Global transition: from ALL non-terminal statuses
      FOR EACH nodeId IN nodes.keys():
        IF nodeId !== transition.toStatusId AND NOT terminalStatusIds.has(nodeId):
          edges.get(nodeId).push(transition)
          incomingEdges.get(transition.toStatusId).push(transition)
    ELSE:
      // Directed transition
      IF transition.fromStatusId AND edges.has(transition.fromStatusId):
        edges.get(transition.fromStatusId).push(transition)
        incomingEdges.get(transition.toStatusId).push(transition)

  RETURN { nodes, edges, incomingEdges, initialStatusId, terminalStatusIds }
```

---

## 1. Complexity Scoring

**File:** `src/algorithms/complexity.ts`

**Goal:** Produce a score 0–100 representing how complex the workflow is. Higher = more complex.

**Formula:**

```
complexityScore = clamp(
  (statusWeight * statusCount) +
  (transitionWeight * transitionCount) +
  (globalWeight * globalTransitionCount) +
  (branchingWeight * branchingFactor) +
  (conditionWeight * conditionDensity),
  0, 100
)
```

**Weights (tunable constants):**
```
STATUS_WEIGHT       = 2.0    // per status above 3 (baseline of 3 is normal)
TRANSITION_WEIGHT   = 1.5    // per transition above 5
GLOBAL_WEIGHT       = 5.0    // per global transition (high complexity signal)
BRANCHING_WEIGHT    = 10.0   // per unit of branching factor above 2.0
CONDITION_WEIGHT    = 3.0    // per avg condition above 1.0
```

**Grade mapping:**
```
A: 0–20
B: 21–40
C: 41–60
D: 61–80
F: 81–100
```

**Pseudocode:**
```
FUNCTION computeComplexity(graph: WorkflowGraph) → ComplexityResult:

  statusCount = graph.nodes.size
  transitionCount = sum of all edges list lengths
  globalTransitionCount = count of transitions with type = 'global'

  // Branching factor: avg number of outgoing transitions per non-terminal status
  nonTerminalNodes = nodes where id NOT IN terminalStatusIds
  totalOutgoing = sum of edges[nodeId].length for nonTerminalNodes
  avgOutdegree = totalOutgoing / max(nonTerminalNodes.size, 1)
  maxOutdegree = max of edges[nodeId].length across all nodes

  // Condition density: avg conditions+validators per transition
  allTransitions = flatten all edges lists (deduplicated by transition id)
  totalConditions = sum of (t.conditionCount + t.validatorCount) for each t
  conditionDensity = totalConditions / max(allTransitions.length, 1)

  // Branching factor relative to baseline
  branchingFactor = avgOutdegree

  rawScore =
    max(statusCount - 3, 0) * STATUS_WEIGHT +
    max(transitionCount - 5, 0) * TRANSITION_WEIGHT +
    globalTransitionCount * GLOBAL_WEIGHT +
    max(branchingFactor - 2.0, 0) * BRANCHING_WEIGHT +
    max(conditionDensity - 1.0, 0) * CONDITION_WEIGHT

  score = clamp(rawScore, 0, 100)
  grade = gradeFromScore(score)   // A/B/C/D/F

  RETURN {
    score, grade,
    breakdown: { statusCount, transitionCount, globalTransitionCount,
                 avgOutdegree, maxOutdegree, conditionDensity, branchingFactor }
  }
```

---

## 2. Dead State Detection

**File:** `src/algorithms/deadState.ts`

**Goal:** Find statuses from which no path exists to any terminal (Done) status.

**Algorithm:** Reverse reachability from terminal nodes using BFS.

```
FUNCTION detectDeadStates(graph: WorkflowGraph) → DeadState[]:

  // STEP 1: Find all statuses reachable BACKWARDS from terminal statuses
  // i.e., all statuses that CAN eventually reach a terminal status
  canReachTerminal = new Set<string>()
  queue = [...graph.terminalStatusIds]

  FOR EACH terminalId IN queue:
    canReachTerminal.add(terminalId)

  WHILE queue is not empty:
    current = queue.dequeue()
    FOR EACH incomingTransition IN graph.incomingEdges.get(current):
      sourceId = incomingTransition.fromStatusId
      IF sourceId AND NOT canReachTerminal.has(sourceId):
        canReachTerminal.add(sourceId)
        queue.enqueue(sourceId)

  // STEP 2: Any status NOT in canReachTerminal is a dead state
  deadStates = []

  FOR EACH [statusId, status] IN graph.nodes:
    IF NOT canReachTerminal.has(statusId):
      // Determine reason
      outgoing = graph.edges.get(statusId) ?? []
      reason = outgoing.length === 0
        ? 'no_outgoing_transitions'
        : 'no_path_to_terminal'

      // Find which statuses can reach this dead state (for reporting)
      reachableFrom = findStatusesThatCanReach(graph, statusId)

      deadStates.push({
        statusId,
        statusName: status.name,
        reason,
        reachableFrom
      })

  RETURN deadStates

FUNCTION findStatusesThatCanReach(graph, targetId) → string[]:
  // BFS backwards from targetId using incomingEdges
  visited = new Set()
  queue = [targetId]
  WHILE queue not empty:
    current = queue.dequeue()
    FOR EACH incoming IN graph.incomingEdges.get(current):
      src = incoming.fromStatusId
      IF src AND NOT visited.has(src):
        visited.add(src)
        queue.enqueue(src)
  visited.delete(targetId)
  RETURN [...visited]
```

---

## 3. Cycle / Loop Detection

**File:** `src/algorithms/cycles.ts`

**Goal:** Find all cycles in the workflow graph. Report each cycle as an ordered list of status IDs.

**Algorithm:** DFS with three-color marking (white/gray/black).

```
FUNCTION detectCycles(graph: WorkflowGraph) → Cycle[]:

  color = Map<string, 'white' | 'gray' | 'black'>()
  FOR EACH nodeId IN graph.nodes.keys():
    color.set(nodeId, 'white')

  cycles = []
  parent = Map<string, string | null>()
  path = []    // current DFS path (stack)

  FUNCTION dfs(nodeId: string):
    color.set(nodeId, 'gray')
    path.push(nodeId)

    FOR EACH transition IN (graph.edges.get(nodeId) ?? []):
      neighbor = transition.toStatusId

      IF color.get(neighbor) === 'gray':
        // Found a back edge → cycle detected
        cycleStart = path.indexOf(neighbor)
        cycleNodes = path.slice(cycleStart)
        cycles.push(buildCycle(graph, cycleNodes, transition))

      ELSE IF color.get(neighbor) === 'white':
        dfs(neighbor)

    path.pop()
    color.set(nodeId, 'black')

  FOR EACH [nodeId] IN graph.nodes:
    IF color.get(nodeId) === 'white':
      dfs(nodeId)

  // Deduplicate cycles (same set of nodes in different rotation)
  RETURN deduplicateCycles(cycles)

FUNCTION buildCycle(graph, statusIds, backEdgeTransition) → Cycle:
  statusNames = statusIds.map(id → graph.nodes.get(id).name)
  transitionNames = [] // collect transition names along path
  // ... build transition name list by traversing edges between consecutive statusIds
  RETURN {
    statusIds,
    statusNames,
    length: statusIds.length,
    transitionNames
  }

FUNCTION deduplicateCycles(cycles: Cycle[]) → Cycle[]:
  // Two cycles are the same if their sorted status ID sets match
  seen = new Set<string>()
  result = []
  FOR EACH cycle IN cycles:
    key = [...cycle.statusIds].sort().join(',')
    IF NOT seen.has(key):
      seen.add(key)
      result.push(cycle)
  RETURN result
```

---

## 4. Path Length Analysis

**File:** `src/algorithms/pathLength.ts`

**Goal:** For each status, compute shortest and longest simple paths to terminal statuses.

**Algorithm:** BFS for shortest path, DFS with backtracking for longest simple path.

```
FUNCTION analyzePathLengths(graph: WorkflowGraph) → PathAnalysis:

  initialId = graph.initialStatusId
  terminalIds = graph.terminalStatusIds

  IF initialId is null:
    RETURN empty PathAnalysis with unreachableStatuses = all statuses

  // BFS: shortest path from initial to all reachable statuses
  shortestFromInitial = bfsShortestPaths(graph, initialId)

  // Find unreachable statuses (not reachable from initial)
  unreachableStatuses = []
  FOR EACH nodeId IN graph.nodes.keys():
    IF shortestFromInitial.get(nodeId) === undefined:
      unreachableStatuses.push(nodeId)

  // Shortest path to any terminal
  shortestToTerminal = Infinity
  FOR EACH terminalId IN terminalIds:
    dist = shortestFromInitial.get(terminalId)
    IF dist < shortestToTerminal:
      shortestToTerminal = dist

  // Longest simple path from initial to any terminal (DFS with backtracking)
  longestToTerminal = dfsLongestPath(graph, initialId, terminalIds)

  // Average: mean of shortest paths from initial to each terminal
  terminalDistances = [...terminalIds].map(id → shortestFromInitial.get(id)).filter(defined)
  averagePathLength = mean(terminalDistances)

  RETURN {
    shortestPathToTerminal: shortestToTerminal,
    longestPathToTerminal: longestToTerminal,
    averagePathLength,
    unreachableStatuses,
    pathDetails: []   // optional detail per terminal pair
  }

FUNCTION bfsShortestPaths(graph, startId) → Map<string, number>:
  distances = new Map()
  distances.set(startId, 0)
  queue = [startId]
  WHILE queue not empty:
    current = queue.dequeue()
    FOR EACH transition IN graph.edges.get(current):
      neighbor = transition.toStatusId
      IF NOT distances.has(neighbor):
        distances.set(neighbor, distances.get(current) + 1)
        queue.enqueue(neighbor)
  RETURN distances

FUNCTION dfsLongestPath(graph, startId, terminalIds) → number:
  // DFS with visited set to avoid revisiting (simple path)
  // Returns maximum hop count to any terminal
  maxLen = 0
  visited = new Set()

  FUNCTION dfs(nodeId, depth):
    nonlocal maxLen
    IF terminalIds.has(nodeId):
      maxLen = max(maxLen, depth)
      RETURN
    visited.add(nodeId)
    FOR EACH transition IN graph.edges.get(nodeId):
      neighbor = transition.toStatusId
      IF NOT visited.has(neighbor):
        dfs(neighbor, depth + 1)
    visited.delete(nodeId)

  dfs(startId, 0)
  RETURN maxLen
```

---

## 5. Workflow Drift Comparison

**File:** `src/algorithms/drift.ts`

**Goal:** Compare two workflows and quantify how different they are.

**Algorithm:** Set operations on status names and transition signatures.

```
FUNCTION compareWorkflows(detailA: WorkflowDetail, detailB: WorkflowDetail) → DriftResult:

  // Status comparison (by name, case-insensitive)
  statusNamesA = new Set(detailA.statuses.map(s → s.name.toLowerCase()))
  statusNamesB = new Set(detailB.statuses.map(s → s.name.toLowerCase()))

  addedStatuses   = detailB.statuses.filter(s → NOT statusNamesA.has(s.name.lower()))
  removedStatuses = detailA.statuses.filter(s → NOT statusNamesB.has(s.name.lower()))
  commonStatuses  = detailA.statuses.filter(s → statusNamesB.has(s.name.lower()))

  // Transition comparison (by signature: fromName→toName, case-insensitive)
  transitionSigA = Map of signature → transition for detailA
  transitionSigB = Map of signature → transition for detailB

  FUNCTION signature(t: WorkflowTransition, statuses: WorkflowStatus[]) → string:
    fromName = statuses.find(s → s.id === t.fromStatusId)?.name ?? 'START'
    toName   = statuses.find(s → s.id === t.toStatusId)?.name ?? 'END'
    RETURN `${fromName.lower()}→${toName.lower()}`

  addedTransitions   = transitions in B not in A (by signature)
  removedTransitions = transitions in A not in B (by signature)
  commonTransitions  = transitions in both (by signature)

  // Changed transitions: same signature but different condition/validator counts
  changedTransitions = []
  FOR EACH sig IN intersection(sigA.keys(), sigB.keys()):
    tA = transitionSigA.get(sig)
    tB = transitionSigB.get(sig)
    changes = detectTransitionChanges(tA, tB)
    IF changes.length > 0:
      changedTransitions.push({ transitionId: tB.id, transitionName: tB.name, changes })

  // Drift score: weighted sum of differences relative to total elements
  totalElements = max(statusNamesA.size + detailA.transitions.length,
                      statusNamesB.size + detailB.transitions.length)
  diffs = addedStatuses.length + removedStatuses.length +
          addedTransitions.length + removedTransitions.length +
          changedTransitions.length * 0.5
  driftScore = clamp((diffs / max(totalElements, 1)) * 100, 0, 100)

  RETURN {
    workflowA: toSummary(detailA),
    workflowB: toSummary(detailB),
    driftScore,
    addedStatuses, removedStatuses,
    addedTransitions, removedTransitions,
    changedTransitions, commonStatuses, commonTransitions
  }
```

---

## 6. Health / Technical Debt Score

**File:** `src/algorithms/health.ts`

**Goal:** Produce a composite health score 0–100 (higher = healthier) and a debt item list.

**Algorithm:** Penalty-based formula using results from all other algorithms.

```
FUNCTION computeHealthScore(
  complexity: ComplexityResult,
  deadStates: DeadState[],
  cycles: Cycle[],
  paths: PathAnalysis
) → HealthScore:

  // Start at 100 and deduct penalties
  baseScore = 100

  // Complexity penalty: if complexity score > 40, deduct proportionally
  complexityPenalty = max(complexity.score - 40, 0) * 0.3   // max 18 pts

  // Dead state penalty: 10 points per dead state (max 30)
  deadStatePenalty = min(deadStates.length * 10, 30)

  // Cycle penalty: 8 points per cycle (max 24)
  cyclePenalty = min(cycles.length * 8, 24)

  // Long path penalty: if longest path > 10 hops, deduct 2 per extra hop (max 10)
  longPathPenalty = min(max(paths.longestPathToTerminal - 10, 0) * 2, 10)

  // Unreachable status penalty: 5 per unreachable status (max 15)
  unreachablePenalty = min(paths.unreachableStatuses.length * 5, 15)

  totalPenalty = complexityPenalty + deadStatePenalty + cyclePenalty +
                 longPathPenalty + unreachablePenalty

  overall = clamp(baseScore - totalPenalty, 0, 100)
  grade = gradeFromScore(100 - overall)   // invert: low health = bad grade

  // Build debt items
  debtItems = []

  FOR EACH deadState IN deadStates:
    debtItems.push({
      severity: 'critical',
      category: 'dead_state',
      message: `Status "${deadState.statusName}" has no path to any Done status`,
      affectedIds: [deadState.statusId]
    })

  FOR EACH cycle IN cycles:
    debtItems.push({
      severity: 'warning',
      category: 'cycle',
      message: `Cycle detected: ${cycle.statusNames.join(' → ')}`,
      affectedIds: cycle.statusIds
    })

  IF complexity.score > 60:
    debtItems.push({
      severity: 'warning',
      category: 'complexity',
      message: `High complexity score (${complexity.score}/100) — consider simplifying`,
      affectedIds: []
    })

  FOR EACH unreachableId IN paths.unreachableStatuses:
    statusName = // look up from analysis context
    debtItems.push({
      severity: 'warning',
      category: 'unreachable',
      message: `Status is unreachable from the initial state`,
      affectedIds: [unreachableId]
    })

  IF paths.longestPathToTerminal > 10:
    debtItems.push({
      severity: 'info',
      category: 'long_path',
      message: `Longest path to completion is ${paths.longestPathToTerminal} steps`,
      affectedIds: []
    })

  RETURN {
    overall,
    grade,
    debtItems,
    breakdown: { complexityPenalty, deadStatePenalty, cyclePenalty,
                 longPathPenalty, unreachablePenalty }
  }
```

---

## Shared Helpers

**File:** `src/algorithms/graph.ts` (also include these)

```typescript
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function gradeFromScore(score: number): 'A' | 'B' | 'C' | 'D' | 'F' {
  if (score <= 20) return 'A';
  if (score <= 40) return 'B';
  if (score <= 60) return 'C';
  if (score <= 80) return 'D';
  return 'F';
}

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}
```

---

## Testing Strategy

Every algorithm file must have a corresponding test file: `src/algorithms/__tests__/*.test.ts`

**Required test cases per algorithm:**

| Algorithm | Test Cases |
|-----------|-----------|
| buildGraph | empty workflow, single status, linear chain, branching, global transitions |
| complexityScore | simple (grade A), complex (grade F), edge cases |
| detectDeadStates | no dead states, one dead state, multiple, all dead |
| detectCycles | no cycles, one self-loop, one 2-cycle, one 3-cycle, multiple cycles |
| pathLengths | single path, branching paths, unreachable status, no terminal |
| compareWorkflows | identical workflows (drift=0), completely different (drift≈100), partial overlap |
| healthScore | perfect workflow, critical issues, all penalties combined |
