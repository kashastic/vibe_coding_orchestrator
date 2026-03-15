# Orchestrator Vision

## Goal

Build a local-first autonomous coding orchestrator that:

- reads tasks from a Notion database
- runs Codex locally to implement them
- keeps Notion as the task system of record
- sends high-signal notifications through `ntfy.sh`
- supports long-running autonomous execution with minimal manual supervision
- escalates cleanly to a human only when truly necessary

The orchestrator should feel like a reliable operator for the repo, not a fragile batch script.

---

## Core Workflow Vision

The intended operating model is:

1. Query Notion for the next Codex task.
2. Reconcile Notion against actual repository state before selecting work.
2. Respect dependency ordering.
3. Run Codex non-interactively for normal implementation work.
4. Verify that the expected repository artifact was actually created or updated.
5. Update Notion status correctly.
6. Continue automatically until the queue is complete or truly blocked.

This should work with minimal intervention for normal coding tasks.

An important requirement is that Notion must not drift from reality. The orchestrator should not just read Notion; it should continuously maintain it.

---

## Notion Reconciliation Vision

The Notion method and state maintenance must be treated as a core orchestrator responsibility.

Required behavior:

- every time the orchestrator starts, it should reconcile task statuses against current repository state
- every time it loops, it should keep Notion aligned with what is actually true locally
- any task not in `Todo` should be cross-verified against the current repo state where possible
- if a task is marked `Done` in Notion but its required artifact or validation is missing locally, the orchestrator should correct that status
- if a task is marked `Doing` but no orchestrator run is actually executing it, the orchestrator should recover it into the correct state
- if tasks are `Blocked`, `Failed`, or `Waiting on Human`, the orchestrator should determine whether those states are still valid or should be cleared

The user expectation is:

- Notion should always reflect actual project truth
- status maintenance should be automatic
- the orchestrator should actively repair drift instead of assuming Notion is accurate

The exact reconciliation logic can be pragmatic, but the result must be that Notion remains a live mirror of repo reality.

---

## Human-in-the-Loop Vision

The orchestrator must support a strong human escalation path.

When a task hits a blocker that needs a person, such as:

- `forge login`
- missing API keys or tokens
- approvals
- external authentication
- environment setup

the orchestrator should:

1. detect the blocker clearly
2. notify the user via `ntfy`
3. mark the task as `Waiting on Human`
4. open a separate interactive Codex terminal
5. instruct that interactive session to resolve only the blocker
6. keep Notion and orchestration control in the main orchestrator process
7. resume the same task automatically after the interactive session exits

The user’s preferred experience is:

- the orchestrator remains the controlling process
- the human only steps in for the exact blocker
- the interactive Codex session does not take over the entire workflow
- after the blocker is resolved, the orchestrator continues from that exact task

Another important requirement:

- the orchestrator must not open an interactive Codex terminal that then quietly completes the whole task on its own while the main orchestrator loses visibility

That behavior is undesirable because:

- it breaks the orchestrator’s role as control plane
- it makes Notion updates and notifications lag or disappear
- it creates ambiguity about which agent owns the task outcome

The desired fix is:

- the interactive terminal should resolve only the blocker
- after blocker resolution it should return control to the orchestrator
- the orchestrator should then retry and complete the actual task itself
- if an interactive agent starts doing full task execution, that is a design bug and should be constrained by prompt, process model, or both

---

## Status Model Vision

Notion statuses should reflect real workflow state, not just success/failure:

- `Todo`
- `Doing`
- `Done`
- `Blocked`
- `Failed`
- `Waiting on Human`

Meaning:

- `Todo`: eligible work
- `Doing`: currently in progress
- `Done`: completed and verified
- `Blocked`: cannot continue because of dependency or hard blocker
- `Failed`: Codex executed but task still failed
- `Waiting on Human`: requires user action before retry

The orchestrator should never mark a task `Done` unless the expected local artifact exists.

---

## Dependency Handling Vision

Dependencies must be first-class workflow behavior.

Required behavior:

- do not run tasks whose dependencies are not `Done`
- if an upstream task fails, automatically mark descendants appropriately
- if an upstream task needs human action, downstream tasks should also be blocked from proceeding
- when the upstream blocker is cleared, downstream tasks should be able to return to `Todo`

The user does not want to manually reason through the dependency graph each time something fails.

---

## Notification Vision

Notifications should be actionable, not generic.

The orchestrator should notify for:

- task start
- task finish
- task failure
- waiting on human
- interactive session started
- interactive session finished
- task resuming after blocker resolution
- queue fully blocked
- no tasks remaining

Notifications should include:

- task id
- concise reason
- required human action when applicable

The user should be able to understand what happened from the notification alone, then use logs only for detail.

---

## Logging Vision

The orchestrator should produce durable local logs for every run.

Required logging:

- per-task attempt logs
- orchestrator event log
- structured run ledger

Desired contents:

- task id
- timestamp
- exact Codex command used
- stdout/stderr
- failure reason
- blocker propagation events
- interactive handoff events

The logs should make debugging and recovery straightforward for a new agent or for the user.

---

## Reliability Vision

The orchestrator should be stable for long autonomous runs.

That means:

- retry transient execution failures
- detect missing Codex CLI cleanly
- detect environment issues cleanly
- avoid false-positive success
- avoid false-positive blocker detection
- keep running after single-task failures
- distinguish between:
  - all tasks completed
  - tasks remain but all are blocked

The workflow should degrade gracefully rather than collapse on first error.

---

## Repository Truth Vision

Repository state is authoritative.

If Notion and the local repo disagree:

- trust the code and files on disk
- do not treat Notion `Done` as valid if required repo artifacts do not exist
- use artifact validation and local-state checks to detect drift

The orchestrator should actively guard against status drift instead of assuming Notion is correct.

This applies especially to Notion reconciliation:

- `Done` should be challenged if local artifacts do not support it
- `Doing` should not persist forever after abandoned or crashed runs
- `Blocked` and `Waiting on Human` should be revisited on each run
- the orchestrator should behave like a repair loop, not only an execution loop

---

## Operator Experience Vision

The user wants the orchestrator to feel like a practical autonomous operator:

- simple command to run
- minimal babysitting
- clear handoff only when needed
- main workflow continues automatically after human help
- no confusion about whether the orchestrator or the interactive agent is in control

The desired command style is still simple:

```powershell
python -m orchestrator.orchestrator --interactive-on-blocker
```

But behind that simple interface, the system should:

- manage state robustly
- preserve control in the main process
- recover from blockers intelligently

The user also wants a multi-agent future:

- some tasks should be handoffable to Claude as well as Codex
- the orchestrator should support routing by assigned agent in Notion
- if Claude runs out of context, there should be a structured handoff mechanism so work can continue without losing state

That means the orchestrator ecosystem should eventually support:

- assigning selected tasks to `Claude`
- preserving rolling project memory in repo files
- enabling a later Claude session to pick up from:
  - `claude.md`
  - `rolling_handoff.md`
  - current repo state
  - task-specific logs
  - Notion task metadata

The user expectation is not just task execution, but reliable agent continuity across sessions and across agents.

---

## Current User Expectations

At this point, the user expects the orchestrator to:

- run Codex locally in non-interactive mode by default
- open a new interactive terminal only when human help is required
- keep the main orchestrator terminal alive
- resume the same task after the blocker is resolved
- sync task status back to Notion correctly
- notify the user at important lifecycle events
- avoid unnecessary repeated blocker loops
- be understandable by future agents through repo documentation
- reconcile Notion status with project reality on every run
- eventually support Claude task handoff and context recovery cleanly

---

## Design Principle

The orchestrator should be:

- local-first
- modular
- explicit
- resilient
- auditable
- easy to resume

It is not just a task runner. It is the control plane for autonomous repo execution with human escalation when necessary.
