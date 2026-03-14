from __future__ import annotations

import sys

from orchestrator.codex_runner import CodexRunner
from orchestrator.config import load_config
from orchestrator.logger import RunLogger
from orchestrator.notion_client import NotionAPIError, NotionClient
from orchestrator.ntfy_notifier import NtfyNotifier, NotificationError
from orchestrator.status_updater import StatusUpdater
from orchestrator.task_selector import choose_next_task


def main() -> int:
    run_logger: RunLogger | None = None
    task = None
    try:
        config = load_config()
        notifier = NtfyNotifier(config.ntfy_topic)
        notion_client = NotionClient(
            api_key=config.notion_api_key,
            database_id=config.notion_database_id,
            notion_version=config.notion_version,
        )
        status_updater = StatusUpdater(notion_client)
        run_logger = RunLogger(config.log_dir, config.run_log_path)
        codex_runner = CodexRunner(config.codex_command, config.repo_path)

        selection = choose_next_task(notion_client)
        if selection.task is None:
            notifier.send("Codex", "All tasks completed")
            print("No tasks remaining.")
            return 0

        task = selection.task
        if selection.blocked_reason:
            status_updater.mark_blocked(task, selection.blocked_reason)
            notifier.send("Codex Task Failed", f"{task.task_id} failed")
            run_logger.append_run(
                run_logger.build_record(
                    task_id=task.task_id,
                    task_title=task.title,
                    status="blocked",
                    return_code=None,
                    duration_seconds=None,
                    log_path=None,
                    error=selection.blocked_reason,
                )
            )
            print(selection.blocked_reason)
            return 1

        task = selection.task
        # Notification delivery is validated before Codex starts executing the task.
        notifier.send("Codex Task Started", f"{task.display_name} started")
        status_updater.mark_doing(task)

        log_path = run_logger.task_output_path(task.task_id)
        result = codex_runner.run(task, log_path)

        if result.succeeded:
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
            print(f"Task completed: {task.display_name}")
            return 0

        failure_reason = (
            f"Codex exited with code {result.return_code}. Output logged to {result.log_path}."
        )
        status_updater.mark_blocked(task, failure_reason)
        notifier.send("Codex Task Failed", f"{task.task_id} failed")
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
        print(failure_reason)
        return result.return_code or 1
    except (NotionAPIError, NotificationError, OSError, ValueError) as exc:
        if run_logger is not None:
            run_logger.append_run(
                run_logger.build_record(
                    task_id=task.task_id if task is not None else "SYSTEM",
                    task_title=task.title if task is not None else "orchestrator startup",
                    status="error",
                    return_code=None,
                    duration_seconds=None,
                    log_path=None,
                    error=str(exc),
                )
            )
        print(f"Orchestrator error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
