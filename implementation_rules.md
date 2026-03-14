# implementation_rules.md — Coding Standards and Rules
# Workflow Analyzer — Jira Cloud Forge Application

> Codex must follow ALL rules in this file.
> These rules ensure consistency across the codebase and alignment with Forge constraints.

---

## Rule 1: File and Folder Structure

Always follow the structure defined in `repo_structure.md`. Do not create files outside that structure without updating `repo_structure.md` and `claude.md`.

```
workflow-analyzer/
├── src/
│   ├── resolvers/     ← Forge backend functions only
│   ├── algorithms/    ← Pure analysis logic only, no Forge/Jira deps
│   ├── ui/            ← React components only, no business logic
│   └── types/         ← Shared TypeScript types only
```

**Never** put business logic (analysis algorithms) inside React components.
**Never** put Jira API calls inside React components.
**Never** call `requestJira()` from `src/ui/` files.

---

## Rule 2: TypeScript

- All files must be `.ts` or `.tsx`. No `.js` files.
- Always import types with `import type { ... }` (separate from value imports).
- No `any` types. Use `unknown` when the type is truly unknown, then narrow it.
- Enable strict mode in `tsconfig.json`.
- All function parameters and return types must be explicitly typed.

```typescript
// ✅ CORRECT
function computeComplexity(graph: WorkflowGraph): ComplexityResult { ... }

// ❌ WRONG
function computeComplexity(graph: any): any { ... }
```

---

## Rule 3: Pure Algorithms

All files in `src/algorithms/` must be pure:

- No side effects
- No `console.log` in production code (use structured logging in resolvers only)
- No async functions
- No Forge imports (`@forge/api`, `@forge/storage`, etc.)
- Input → Output only
- All functions must be exported and individually testable

---

## Rule 4: Forge API Usage

Only use these Forge packages:
- `@forge/api` — for `requestJira()` and `storage`
- `@forge/bridge` — for `invoke()` in Custom UI
- `@forge/resolver` — for resolver definitions

**Requesting Jira API (backend only):**
```typescript
import { requestJira } from '@forge/api';

const response = await requestJira('/rest/api/3/workflow/search', {
  method: 'GET',
});
const data = await response.json();
```

**Forge Storage (backend only):**
```typescript
import { storage } from '@forge/api';

// Write
await storage.set('key', value);

// Read
const value = await storage.get('key');

// Delete
await storage.delete('key');
```

---

## Rule 5: Resolver Pattern

All resolvers must follow this pattern:

```typescript
// src/resolvers/index.ts
import Resolver from '@forge/resolver';
const resolver = new Resolver();

resolver.define('functionName', async ({ payload, context }) => {
  // Validate payload
  // Call Jira API if needed
  // Run algorithm
  // Cache to Forge Storage
  // Return typed result
});

export const handler = resolver.getDefinitions();
```

Each resolver function must:
1. Handle errors gracefully (try/catch, return error shape)
2. Check Forge Storage cache before calling Jira API
3. Log errors to console (Forge logs them, not exposed to browser)

---

## Rule 6: Custom UI / React

- Use functional components only (no class components)
- Use React hooks only (`useState`, `useEffect`, `useContext`, `useReducer`, `useMemo`)
- Use `@forge/bridge` for all backend calls:

```typescript
import { invoke } from '@forge/bridge';

const dashboard = await invoke<HealthDashboard>('getHealthDashboard', {});
```

- Do not use any state management libraries (Redux, Zustand, MobX)
- Use React Context + `useReducer` for global state
- No CSS-in-JS libraries — use CSS modules or Atlassian Design System (ADS) components

---

## Rule 7: Atlassian Design System

Use ADS components where available:
- `@atlaskit/button`
- `@atlaskit/spinner`
- `@atlaskit/badge`
- `@atlaskit/table`
- `@atlaskit/lozenge` (for status badges)
- `@atlaskit/page-layout`

Do not build custom button/input/table components when ADS equivalents exist.

---

## Rule 8: Graph Visualization

Use D3.js for the workflow graph visualization:
- Only import D3 in `src/ui/components/WorkflowGraph.tsx`
- Use `useRef` for the SVG element
- Use `useEffect` for D3 rendering (not in the render function)
- Implement force-directed layout (`d3-force`)
- Nodes colored by status category (todo=blue, in_progress=yellow, done=green)
- Highlight dead states in red, cycles in orange

---

## Rule 9: Error Handling

**Backend (resolvers):**
```typescript
try {
  const result = await doSomething();
  return { success: true, data: result };
} catch (error) {
  console.error('Error in resolver:', error);
  return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
}
```

**Frontend (React):**
```typescript
const [error, setError] = useState<string | null>(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  invoke<Dashboard>('getDashboard', {})
    .then(data => setData(data))
    .catch(err => setError(err.message))
    .finally(() => setLoading(false));
}, []);

if (loading) return <Spinner />;
if (error) return <ErrorMessage message={error} />;
```

---

## Rule 10: Caching Strategy

Forge Storage is the cache. Cache TTL is managed manually:
1. Store `last_refresh` as ISO string
2. On each backend request, check if `last_refresh` is older than 1 hour
3. If stale, re-fetch and re-analyze
4. Provide a manual "Refresh" button in the UI that calls `refreshCache`

Cache key naming convention:
- `workflows_list` — all workflow summaries
- `workflow:{workflowId}` — single workflow detail
- `analysis:{workflowId}` — single workflow analysis
- `health_dashboard` — full dashboard data
- `last_refresh` — ISO timestamp

---

## Rule 11: Pagination

Jira's `/workflow/search` returns paginated results. Always fetch all pages:

```typescript
async function fetchAllWorkflows(): Promise<JiraWorkflowRaw[]> {
  const pageSize = 50;
  let startAt = 0;
  const allWorkflows: JiraWorkflowRaw[] = [];

  while (true) {
    const response = await requestJira(
      `/rest/api/3/workflow/search?startAt=${startAt}&maxResults=${pageSize}`
    );
    const page: JiraWorkflowSearchResponse = await response.json();
    allWorkflows.push(...page.values);
    if (page.isLast || allWorkflows.length >= page.total) break;
    startAt += pageSize;
  }

  return allWorkflows;
}
```

---

## Rule 12: Testing

- Use Jest for all tests
- Test file locations: `src/algorithms/__tests__/*.test.ts`
- Run tests: `npm test`
- Minimum coverage: 80% for algorithm files
- No Forge mocks needed for algorithm tests (they are pure functions)
- Do mock `@forge/api` in resolver tests

---

## Rule 13: Manifest Scopes

Only request the minimum required Forge scopes. Current required scopes:
- `read:jira-work`
- `manage:jira-configuration`

Do not add scopes without updating `architecture.md`.

---

## Rule 14: No External AI

Do NOT install or use:
- `openai`, `anthropic`, `@langchain/*`, `@huggingface/*`
- Any ML/AI inference library
- Any external API that uses AI/ML

All analysis must use deterministic algorithms defined in `analysis_algorithms.md`.

---

## Rule 15: Updating Project Memory

After completing each task, Codex must:
1. Update the Notion task status to `Done`
2. Update `rolling_handoff.md` with what was completed and what is next
3. If the task revealed new information (API behavior, algorithm edge case), add a note to `claude.md` under Open Issues or Key Decisions
