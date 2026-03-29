from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from orchestrator.notion_client import Task


@dataclass(frozen=True)
class CodexRunResult:
    return_code: int
    duration_seconds: float
    log_path: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0

    @property
    def command_text(self) -> str:
        return subprocess.list2cmdline(list(self.command))

    @property
    def combined_output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part).strip()


class CodexRunner:
    def __init__(
        self,
        codex_command: str,
        repo_path: Path,
        context_files: tuple[str, ...] = ("claude.md", "rolling_handoff.md", "task_plan.md"),
        timeout_seconds: int | None = None,
    ) -> None:
        self._codex_command = codex_command
        self._repo_path = repo_path
        self._context_files = context_files
        self._timeout_seconds = timeout_seconds

    def build_prompt(self, task: Task) -> str:
        execution_prompt = task.execution_prompt.strip()
        repo_path_text = task.repo_path.strip() or "."
        read_steps = [f"{i + 1}. Read {f}." for i, f in enumerate(self._context_files)]
        next_step = len(self._context_files) + 1
        first_context_file = self._context_files[0] if self._context_files else "claude.md"
        return "\n".join(
            [
                "Execute the following workflow exactly:",
                *read_steps,
                f"{next_step}. Inspect the current repository state before making changes.",
                f"{next_step + 1}. Execute the selected task.",
                f"{next_step + 2}. Update {first_context_file} and rolling_handoff.md before finishing.",
                "",
                f"Repository root: {self._repo_path}",
                "",
                f"Selected task: {task.display_name}",
                f"Primary repo path: {repo_path_text}",
                "",
                "Task instructions:",
                execution_prompt if execution_prompt else "No additional task-specific prompt was provided.",
            ]
        )

    def run(self, task: Task, log_path: Path) -> CodexRunResult:
        prompt = self.build_prompt(task)
        command = tuple(self._build_command())
        start = time.monotonic()
        command_text = subprocess.list2cmdline(list(command))

        try:
            process = subprocess.run(
                list(command),
                cwd=self._repo_path,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=self._timeout_seconds,
            )
            error_message = None
            stdout = process.stdout
            stderr = process.stderr
            return_code = process.returncode
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start
            stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            self._write_log(log_path, command_text, stdout, stderr)
            return CodexRunResult(
                return_code=1,
                duration_seconds=duration,
                log_path=log_path,
                command=command,
                stdout=stdout,
                stderr=stderr,
                error_message=f"Codex timed out after {self._timeout_seconds}s.",
            )
        except OSError as exc:
            duration = time.monotonic() - start
            stdout = ""
            stderr = str(exc)
            self._write_log(log_path, command_text, stdout, stderr)
            return CodexRunResult(
                return_code=1,
                duration_seconds=duration,
                log_path=log_path,
                command=command,
                stdout=stdout,
                stderr=stderr,
                error_message=str(exc),
            )

        duration = time.monotonic() - start
        self._write_log(log_path, command_text, stdout, stderr)
        return CodexRunResult(
            return_code=return_code,
            duration_seconds=duration,
            log_path=log_path,
            command=command,
            stdout=stdout,
            stderr=stderr,
            error_message=error_message,
        )

    def launch_interactive(self, task: Task, blocker_context: str) -> int:
        executable = self._resolve_executable()
        prompt = "\n".join(
            [
                "You are in blocker-resolution mode for the orchestrator.",
                f"Task: {task.display_name}",
                "",
                "Blocker context:",
                blocker_context,
                "",
                "Rules:",
                "1. Resolve only the named blocker.",
                "2. Do not continue the full task after the blocker is resolved.",
                "3. Do not update Notion. The orchestrator handles status updates.",
                "4. Minimize repo changes unless the blocker itself requires them.",
                "5. When the blocker is resolved, stop and tell the human to return control to the orchestrator.",
                "",
                "Work with the human in this terminal only until the blocker is resolved.",
            ]
        )
        command = [executable, prompt]
        command.insert(1, "--dangerously-bypass-approvals-and-sandbox")
        print("Launching interactive Codex session in a new terminal window.")
        print(f"Command: {subprocess.list2cmdline(command)}")
        if not sys.stdin.isatty():
            raise ValueError("Interactive blocker mode requires a real terminal.")
        if sys.platform == "win32":
            process = subprocess.Popen(
                command,
                cwd=self._repo_path,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return process.wait()
        process = subprocess.run(
            command,
            cwd=self._repo_path,
            check=False,
        )
        return process.returncode

    def _build_command(self) -> list[str]:
        if not self._codex_command.strip():
            raise ValueError("CODEX_COMMAND cannot be empty.")

        executable = self._resolve_executable()
        return [
            executable,
            "--dangerously-bypass-approvals-and-sandbox",
            "exec",
            "-",
        ]

    def _resolve_executable(self) -> str:
        executable = shutil.which(self._codex_command)
        if executable is None:
            raise ValueError(
                f"Codex CLI '{self._codex_command}' was not found on PATH. "
                "Install the Codex CLI v0.114+ and ensure the executable is available."
            )
        return executable

    def _write_log(self, log_path: Path, command_text: str, stdout: str, stderr: str) -> None:
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(f"Launching Codex command: {command_text}\n")
            handle.write(f"Working directory: {self._repo_path}\n\n")
            if stdout:
                handle.write("STDOUT:\n")
                handle.write(stdout)
                if not stdout.endswith("\n"):
                    handle.write("\n")
            if stderr:
                handle.write("\nSTDERR:\n")
                handle.write(stderr)
                if not stderr.endswith("\n"):
                    handle.write("\n")
