from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from dataclasses import dataclass

from orchestrator.claude_handoff import build_handoff
from orchestrator.codex_runner import CodexRunner
from orchestrator.config import load_config
from orchestrator.logger import RunLogger
from orchestrator.notion_client import NotionAPIError, NotionClient, Task
from orchestrator.ntfy_notifier import NtfyNotifier, NotificationError
from orchestrator.status_updater import StatusUpdater
from orchestrator.task_selector import choose_next_task
from orchestrator.task_reconciler import plan_reconciliation, task_artifact_exists

MAX_RETRIES = 2


@dataclass(frozen=True)
class HumanBlocker:
    reason: str
    action: str


def main(argv: list[str] | None = None) -> int:
    run_logger: RunLogger | None = None
    try:
        args = _parse_args(argv)
        config = load_config()
        notifier = NtfyNotifier(config.ntfy_topic)
        notion_client = NotionClient(
            api_key=config.notion_api_key,
            database_id=config.notion_database_id,
            notion_version=config.notion_version,
        )
        status_updater = StatusUpdater(notion_client)
        run_logger = RunLogger(config.log_dir, config.run_log_path)
        codex_runner = CodexRunner(
            config.codex_command,
            config.repo_path,
            config.context_files,
            config.codex_timeout_seconds,
        )
        first_iteration = True

        while True:
            if not first_iteration:
                time.sleep(config.loop_sleep_seconds)
            first_iteration = False
            try:
                all_tasks = notion_client.query_tasks_for_agents(("Codex", "Claude"))
                _reconcile_notion_state(
                    all_tasks=all_tasks,
                    notifier=notifier,
                    run_logger=run_logger,
                    status_updater=status_updater,
                    repo_root=config.repo_path,
                )
                all_tasks = notion_client.query_tasks_for_agents(("Codex", "Claude"))
                reset_tasks = status_updater.reset_auto_blocked_descendants(all_tasks=all_tasks)
                for reset_task in reset_tasks:
                    run_logger.log_event(
                        task_id=reset_task.task_id,
                        command=None,
                        message="Automatically reset descendant task back to Todo after blocker status changed",
                    )
                if reset_tasks:
                    all_tasks = notion_client.query_tasks_for_agents(("Codex", "Claude"))

                _prepare_claude_handoffs(
                    all_tasks=all_tasks,
                    notifier=notifier,
                    run_logger=run_logger,
                    status_updater=status_updater,
                    repo_root=config.repo_path,
                )

                selection = choose_next_task(notion_client, all_tasks)
                if selection.task is None:
                    incomplete_tasks = [task for task in all_tasks if task.status != "Done"]
                    blocked_tasks = [
                        task for task in incomplete_tasks if task.status in {"Blocked", "Waiting on Human", "Failed"}
                    ]
                    if blocked_tasks:
                        notifier.send("Codex Blocked", "Tasks remain, but all available work is blocked")
                        if run_logger is not None:
                            run_logger.log_event(
                                task_id="SYSTEM",
                                command=None,
                                message="Tasks remain, but all available work is blocked",
                            )
                        print("Tasks remain, but all available work is blocked.")
                        return 1
                    else:
                        notifier.send("Codex", "All tasks completed")
                        print("No tasks remaining.")
                        return 0

                task = selection.task
                if selection.blocked_reason:
                    _record_blocked_task(
                        run_logger,
                        status_updater,
                        notifier,
                        task_id=task.task_id,
                        task_title=task.title,
                        task=task,
                        reason=selection.blocked_reason,
                    )
                    print(selection.blocked_reason)
                    continue

                local_state_issue = _local_state_blocker(task, config.repo_path)
                if local_state_issue is not None:
                    _record_blocked_task(
                        run_logger,
                        status_updater,
                        notifier,
                        task_id=task.task_id,
                        task_title=task.title,
                        task=task,
                        reason=local_state_issue,
                    )
                    print(local_state_issue)
                    continue

                notifier.send("Codex Task Started", f"{task.display_name} started")
                status_updater.mark_doing(task)
                result = _run_task_with_retries(codex_runner, run_logger, task)
                human_blocker = _detect_human_blocker(result)

                if human_blocker is not None:
                    rerun_result = _handle_human_blocker(
                        args=args,
                        codex_runner=codex_runner,
                        notifier=notifier,
                        run_logger=run_logger,
                        status_updater=status_updater,
                        task=task,
                        all_tasks=all_tasks,
                        result=result,
                        human_blocker=human_blocker,
                    )
                    if rerun_result is None:
                        continue
                    result = rerun_result

                if result.succeeded:
                    validation_error = _validate_task_artifact(task, config.repo_path)
                    if validation_error is not None:
                        status_updater.mark_failed(task, validation_error)
                        notifier.send(
                            "Codex Task Failed",
                            f"{task.task_id} failed: {validation_error}",
                        )
                        downstream = status_updater.block_descendants(
                            root_task=task,
                            all_tasks=all_tasks,
                            reason=f"Blocked by {task.task_id}: {validation_error}",
                            waiting_on_human=False,
                        )
                        run_logger.append_run(
                            run_logger.build_record(
                                task_id=task.task_id,
                                task_title=task.title,
                                status="failed",
                                return_code=result.return_code,
                                duration_seconds=result.duration_seconds,
                                log_path=result.log_path,
                                error=validation_error,
                            )
                        )
                        run_logger.log_event(
                            task_id=task.task_id,
                            command=result.command_text,
                            message=validation_error,
                            error_output=result.combined_output,
                        )
                        _log_descendant_updates(run_logger, task.task_id, downstream, waiting_on_human=False)
                        print(validation_error)
                        continue

                    status_updater.mark_done(task)
                    notifier.send("Codex Task Finished", f"{task.task_id} completed successfully")
                    run_logger.append_run(
                        run_logger.build_record(
                            task_id=task.task_id,
                            task_title=task.title,
                            status="done",
                            return_code=result.return_code,
                            duration_seconds=result.duration_seconds,
                            log_path=result.log_path,
                            error=None,
                        )
                    )
                    run_logger.log_event(
                        task_id=task.task_id,
                        command=result.command_text,
                        message="Task completed successfully",
                    )
                    print(f"Task completed: {task.display_name}")
                    continue

                failure_reason = _failure_reason(result)
                status_updater.mark_failed(task, failure_reason)
                downstream = status_updater.block_descendants(
                    root_task=task,
                    all_tasks=all_tasks,
                    reason=f"Blocked by {task.task_id}: {failure_reason}",
                    waiting_on_human=False,
                )
                notifier.send(
                    "Codex Task Failed",
                    _failure_notification_message(task.task_id, result),
                )
                run_logger.append_run(
                    run_logger.build_record(
                        task_id=task.task_id,
                        task_title=task.title,
                        status="failed",
                        return_code=result.return_code,
                        duration_seconds=result.duration_seconds,
                        log_path=result.log_path,
                        error=failure_reason,
                    )
                )
                run_logger.log_event(
                    task_id=task.task_id,
                    command=result.command_text,
                    message=failure_reason,
                    error_output=result.stderr or result.stdout,
                )
                _log_descendant_updates(run_logger, task.task_id, downstream, waiting_on_human=False)
                print(failure_reason)
            except (NotionAPIError, NotificationError, OSError, ValueError) as exc:
                if run_logger is not None:
                    run_logger.append_run(
                        run_logger.build_record(
                            task_id="SYSTEM",
                            task_title="orchestrator loop",
                            status="error",
                            return_code=None,
                            duration_seconds=None,
                            log_path=None,
                            error=str(exc),
                        )
                    )
                    run_logger.log_event(
                        task_id="SYSTEM",
                        command=None,
                        message=f"Orchestrator loop error: {exc}",
                        error_output=str(exc),
                    )
                print(f"Orchestrator error: {exc}", file=sys.stderr)
                continue
    except (NotionAPIError, NotificationError, OSError, ValueError) as exc:
        if run_logger is not None:
            run_logger.append_run(
                run_logger.build_record(
                    task_id="SYSTEM",
                    task_title="orchestrator startup",
                    status="error",
                    return_code=None,
                    duration_seconds=None,
                    log_path=None,
                    error=str(exc),
                )
            )
            run_logger.log_event(
                task_id="SYSTEM",
                command=None,
                message=f"Orchestrator startup error: {exc}",
                error_output=str(exc),
            )
        print(f"Orchestrator error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "\nOrchestrator interrupted. Any task currently marked 'Doing' will be "
            "reset to 'Todo' automatically on the next run.",
            file=sys.stderr,
        )
        if run_logger is not None:
            run_logger.log_event(
                task_id="SYSTEM",
                command=None,
                message="Orchestrator interrupted by user (KeyboardInterrupt).",
            )
        return 130


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interactive-on-blocker",
        action="store_true",
        help="Launch an interactive Codex session when a task needs human input.",
    )
    return parser.parse_args(argv)


def _reconcile_notion_state(
    *,
    all_tasks: list[Task],
    notifier: NtfyNotifier,
    run_logger: RunLogger,
    status_updater: StatusUpdater,
    repo_root: Path,
) -> None:
    for action in plan_reconciliation(all_tasks, repo_root):
        status_updater.apply_status(action.task, action.target_status, action.reason)
        run_logger.log_event(
            task_id=action.task.task_id,
            command=None,
            message=f"Reconciled Notion status to {action.target_status}: {action.reason}",
        )
        if action.target_status == "Failed":
            notifier.send("Codex Task Failed", f"{action.task.task_id} reconciled to Failed")


def _prepare_claude_handoffs(
    *,
    all_tasks: list[Task],
    notifier: NtfyNotifier,
    run_logger: RunLogger,
    status_updater: StatusUpdater,
    repo_root: Path,
) -> None:
    by_page_id = {task.page_id: task for task in all_tasks}
    handoff_dir = repo_root / "orchestrator" / "handoffs"
    for task in all_tasks:
        if task.assigned_agent != "Claude":
            continue
        dependencies_done = all(
            by_page_id.get(dependency_id) is not None
            and by_page_id[dependency_id].status == "Done"
            for dependency_id in task.dependency_ids
        )
        if not dependencies_done:
            continue
        if task.status not in {"Todo", "Waiting on Human", "Doing"}:
            continue
        handoff = build_handoff(task, repo_root, handoff_dir)
        run_logger.log_event(
            task_id=task.task_id,
            command=None,
            message=f"Prepared Claude handoff at {handoff.path}",
        )
        if task.status == "Todo":
            status_updater.mark_waiting_on_human(
                task,
                f"Claude handoff ready at {handoff.path}. Use this handoff with claude.md and rolling_handoff.md.",
            )
            notifier.send(
                "Claude Handoff Ready",
                f"{task.task_id} ready for Claude at {handoff.path.name}",
            )


def _run_task_with_retries(
    codex_runner: CodexRunner,
    run_logger: RunLogger,
    task: Task,
):
    attempts = MAX_RETRIES + 1
    last_result = None
    for attempt in range(1, attempts + 1):
        log_path = run_logger.task_output_path(f"{task.task_id}-attempt-{attempt}")
        result = codex_runner.run(task, log_path)
        last_result = result
        run_logger.log_event(
            task_id=task.task_id,
            command=result.command_text,
            message=f"Attempt {attempt} finished with exit code {result.return_code}",
            error_output=result.stderr or result.stdout if not result.succeeded else None,
        )
        if result.succeeded or not _is_retryable_failure(result):
            return result
    return last_result


def _is_retryable_failure(result) -> bool:
    if result.error_message:
        # Timeouts are not transient — retrying would just time out again
        if "timed out" in result.error_message.lower():
            return False
        return True
    failure_text = f"{result.stderr}\n{result.stdout}".lower()
    retry_markers = (
        "winerror 2",
        "file not found",
        "not found on path",
        "system cannot find the file specified",
        "error: stdin is not a terminal",
        "unexpected argument",
        "network",
        "timed out",
    )
    return any(marker in failure_text for marker in retry_markers)


def _failure_reason(result) -> str:
    if result.error_message:
        return result.error_message
    return f"Codex exited with code {result.return_code}. Output logged to {result.log_path}."


def _failure_notification_message(task_id: str, result) -> str:
    detail = (result.stderr or result.stdout or result.error_message or "").strip()
    detail = detail.replace("\r", " ").replace("\n", " ")
    if len(detail) > 160:
        detail = detail[:157] + "..."
    suffix = f": {detail}" if detail else ""
    return f"{task_id} failed{suffix}"


def _detect_human_blocker(result) -> HumanBlocker | None:
    combined = _blocker_detection_text(result)
    rules = (
        (
            (
                "error: not logged in",
                "run `forge login`",
                "run forge login",
                "please run forge login",
                "forge authentication is not available",
            ),
            HumanBlocker(
                reason="Human action required: Forge authentication is missing.",
                action="Run `forge login` in the repo and then reset the task to Todo.",
            ),
        ),
        (
            (
                "missing api key",
                "api key is missing",
                "api token",
                "missing token",
                "missing credential",
                "credentials are missing",
                "secret_",
                "authorization failed",
            ),
            HumanBlocker(
                reason="Human action required: credentials or tokens are missing.",
                action="Provide the required token/env var, then reset the task to Todo.",
            ),
        ),
        (
            (
                "approval required",
                "requires approval",
                "permission denied",
                "access denied",
                "manual approval",
            ),
            HumanBlocker(
                reason="Human action required: an approval or external permission is needed.",
                action="Grant the required approval/permission, then reset the task to Todo.",
            ),
        ),
        (
            (
                "login required",
                "sign in required",
                "authentication required",
                "please sign in",
            ),
            HumanBlocker(
                reason="Human action required: an external login is required.",
                action="Complete the login/authentication step, then reset the task to Todo.",
            ),
        ),
    )
    for markers, blocker in rules:
        if any(marker in combined for marker in markers):
            return blocker
    return None


def _blocker_detection_text(result) -> str:
    if result.error_message:
        return result.error_message.lower()

    combined_output = result.combined_output or ""
    if not combined_output:
        return ""

    final_message = _extract_final_codex_message(combined_output)
    if final_message:
        return final_message.lower()

    return combined_output.lower()


def _extract_final_codex_message(output: str) -> str:
    marker = "\ncodex\n"
    last_marker = output.lower().rfind(marker)
    if last_marker == -1:
        return ""

    final_section = output[last_marker + len(marker) :]
    stop_markers = ("\nfile update", "\nexec\n", "\napply_patch(", "\ntokens used")
    stop_positions = [final_section.lower().find(stop_marker) for stop_marker in stop_markers]
    valid_positions = [position for position in stop_positions if position != -1]
    if valid_positions:
        final_section = final_section[: min(valid_positions)]
    return final_section.strip()


def _log_descendant_updates(
    run_logger: RunLogger,
    root_task_id: str,
    descendants: list[Task],
    *,
    waiting_on_human: bool,
) -> None:
    if not descendants:
        return
    target_status = "Waiting on Human" if waiting_on_human else "Blocked"
    descendant_ids = ", ".join(task.task_id for task in descendants)
    run_logger.log_event(
        task_id=root_task_id,
        command=None,
        message=f"Updated descendants to {target_status}: {descendant_ids}",
    )


def _handle_human_blocker(
    *,
    args: argparse.Namespace,
    codex_runner: CodexRunner,
    notifier: NtfyNotifier,
    run_logger: RunLogger,
    status_updater: StatusUpdater,
    task: Task,
    all_tasks: list[Task],
    result,
    human_blocker: HumanBlocker,
):
    status_updater.mark_waiting_on_human(task, human_blocker.reason)
    downstream = status_updater.block_descendants(
        root_task=task,
        all_tasks=all_tasks,
        reason=f"Blocked by {task.task_id}: {human_blocker.reason}",
        waiting_on_human=True,
    )
    notifier.send(
        "Codex Waiting on Human",
        f"{task.task_id} waiting on human: {human_blocker.action}",
    )
    run_logger.append_run(
        run_logger.build_record(
            task_id=task.task_id,
            task_title=task.title,
            status="waiting_on_human",
            return_code=result.return_code,
            duration_seconds=result.duration_seconds,
            log_path=result.log_path,
            error=human_blocker.reason,
        )
    )
    run_logger.log_event(
        task_id=task.task_id,
        command=result.command_text,
        message=human_blocker.reason,
        error_output=result.combined_output,
    )
    _log_descendant_updates(run_logger, task.task_id, downstream, waiting_on_human=True)
    print(human_blocker.reason)

    if not args.interactive_on_blocker:
        return None

    context = "\n".join(
        [
            human_blocker.reason,
            f"Required action: {human_blocker.action}",
            f"See log: {result.log_path}",
            "Important: resolve only the blocker, then exit the interactive session so the orchestrator can retry the same task.",
        ]
    )
    notifier.send(
        "Codex Interactive Started",
        f"{task.task_id} interactive blocker session started",
    )
    interactive_return_code = codex_runner.launch_interactive(task, context)
    run_logger.log_event(
        task_id=task.task_id,
        command=None,
        message=f"Interactive Codex session exited with code {interactive_return_code}",
    )
    notifier.send(
        "Codex Interactive Finished",
        f"{task.task_id} interactive blocker session exited with code {interactive_return_code}",
    )
    if interactive_return_code != 0:
        return None

    status_updater.mark_todo(task)
    notifier.send(
        "Codex Task Resuming",
        f"{task.task_id} retrying automatically after interactive blocker resolution",
    )
    rerun_result = _run_task_with_retries(codex_runner, run_logger, task)
    rerun_blocker = _detect_human_blocker(rerun_result)
    if rerun_blocker is not None:
        status_updater.mark_waiting_on_human(task, rerun_blocker.reason)
        notifier.send(
            "Codex Waiting on Human",
            f"{task.task_id} still waiting on human: {rerun_blocker.action}",
        )
        return None
    return rerun_result


def _record_blocked_task(
    run_logger: RunLogger,
    status_updater: StatusUpdater,
    notifier: NtfyNotifier,
    *,
    task_id: str,
    task_title: str,
    task: Task,
    reason: str,
) -> None:
    status_updater.mark_blocked(task, reason)
    notifier.send("Codex Task Blocked", f"{task_id} blocked: {reason}")
    run_logger.append_run(
        run_logger.build_record(
            task_id=task_id,
            task_title=task_title,
            status="blocked",
            return_code=None,
            duration_seconds=None,
            log_path=None,
            error=reason,
        )
    )
    run_logger.log_event(
        task_id=task_id,
        command=None,
        message=reason,
        error_output=reason,
    )


def _local_state_blocker(task: Task, repo_root: Path) -> str | None:
    repo_path = task.repo_path.strip()
    if not repo_path:
        return None

    normalized = Path(repo_path)
    parts = normalized.parts
    if len(parts) < 2:
        return None

    top_level = repo_root / parts[0]
    if top_level.exists():
        return None

    if not task.dependency_ids:
        return None

    return (
        f"Repository state drift detected: {parts[0]!r} is missing locally, but "
        f"{task.task_id} targets {repo_path}. Reset upstream tasks to Todo and rerun."
    )


def _validate_task_artifact(task: Task, repo_root: Path) -> str | None:
    repo_path = task.repo_path.strip()
    if not repo_path:
        return None

    if task_artifact_exists(task, repo_root):
        return None

    return (
        f"Task reported success but expected repo path was not created: {repo_path}. "
        "Not marking task Done."
    )


if __name__ == "__main__":
    raise SystemExit(main())
