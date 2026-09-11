#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.integrations.qgis.tasks
~~~~~~~~~~~~~~~

Background subprocess tasks used by the Transformez QGIS plugin.
"""

from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import traceback
from pathlib import Path

from qgis.core import Qgis, QgsMessageLog, QgsTask

from .dependencies import (
    PLUGIN_DIR,
    runtime_create_command,
    runtime_exists,
    runtime_install_command,
    runtime_python,
    runtime_uninstall_command,
)


class TransformezTask(QgsTask):
    """Base task with subprocess cancellation, streaming I/O, and error capture."""

    def __init__(self, description: str):
        super().__init__(description, QgsTask.CanCancel)
        self.error: Exception | None = None
        self.traceback_text: str | None = None
        self.stdout: str = ""
        self.stderr: str = ""
        self.process: subprocess.Popen[str] | None = None

    def _capture_error(self, exc: Exception) -> None:
        self.error = exc
        self.traceback_text = traceback.format_exc()

    def _handle_stdout_line(self, line: str) -> None:
        """Hook for subclasses that consume streaming worker output."""

    _ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    _TQDM_RE = re.compile(
        r"(?:\d{1,3}%\|.*\||\d+/\d+.*(?:it/s|s/it|B/s|MB/s|GB/s))",
        re.IGNORECASE,
    )

    @classmethod
    def _clean_terminal_output(cls, line: str) -> str | None:
        """Normalize terminal-oriented output before sending it to QGIS logs.

        ANSI escape sequences are removed and carriage-return redraws (as used by
        tqdm) are collapsed to their final screen state. Terminal progress bars are
        suppressed entirely because structured Transformez progress is handled by
        QgsTask instead.
        """

        text = cls._ANSI_RE.sub("", line)
        parts = [part.strip() for part in text.split("\r") if part.strip()]
        if not parts:
            return None

        text = parts[-1]
        if cls._TQDM_RE.search(text):
            return None

        return text or None

    def _handle_stderr_line(self, line: str) -> str | None:
        """Forward cleaned subprocess diagnostics to the QGIS Log Messages panel."""
        clean_line = self._clean_terminal_output(line)
        if clean_line is None:
            return None
        else:
            line = clean_line

        upper = line.upper()
        if "CRITICAL" in upper or "FATAL" in upper:
            level = Qgis.MessageLevel.Critical
        elif "ERROR" in upper or "TRACEBACK" in upper:
            level = Qgis.MessageLevel.Critical
        elif "WARNING" in upper or "WARN" in upper:
            level = Qgis.MessageLevel.Warning
        else:
            level = Qgis.MessageLevel.Info

        QgsMessageLog.logMessage(line, "Transformez", level=level)
        return line

    def _run_process(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str] | None:
        """Run a child process while continuously draining stdout and stderr.

        Both pipes must be drained while the process is alive. Waiting for process
        termination before reading them can deadlock when either OS pipe buffer fills.
        """

        self.stdout = ""
        self.stderr = ""

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if input_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        if input_text is not None and self.process.stdin is not None:
            self.process.stdin.write(input_text)
            self.process.stdin.close()
            self.process.stdin = None

        output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

        def drain(name: str, stream) -> None:
            try:
                for line in iter(stream.readline, ""):
                    output_queue.put((name, line))
            finally:
                output_queue.put((name, None))
                stream.close()

        assert self.process.stdout is not None
        assert self.process.stderr is not None

        stdout_thread = threading.Thread(
            target=drain,
            args=("stdout", self.process.stdout),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=drain,
            args=("stderr", self.process.stderr),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        closed_streams: set[str] = set()

        while self.process.poll() is None or len(closed_streams) < 2:
            if self.isCanceled() and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()

            try:
                name, line = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if line is None:
                closed_streams.add(name)
                continue

            if name == "stdout":
                self.stdout += line
                self._handle_stdout_line(line.rstrip("\r\n"))
            else:
                cleaned = self._handle_stderr_line(line.rstrip("\n"))
                if cleaned:
                    self.stderr += cleaned + "\n"

        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        returncode = self.process.wait()
        return subprocess.CompletedProcess(
            command,
            returncode,
            self.stdout,
            self.stderr,
        )


class InstallTransformezTask(TransformezTask):
    """Create/update the isolated Transformez runtime in the background."""

    def __init__(self, source: str | Path | None = None):
        super().__init__("Install isolated Transformez runtime")
        self.source = Path(source) if source is not None else None
        self.result: subprocess.CompletedProcess[str] | None = None
        self.stage: str = "initializing"

    def run(self) -> bool:
        try:
            if self.isCanceled():
                return False

            if not runtime_exists():
                self.stage = "creating virtual environment"
                self.setProgress(10)
                result = self._run_process(runtime_create_command())
                if result is None:
                    return False
                if result.returncode != 0:
                    self.result = result
                    return False

            self.stage = "installing Transformez"
            self.setProgress(35)
            self.result = self._run_process(runtime_install_command(self.source))
            if self.result is None:
                return False
            if self.isCanceled():
                return False

            self.setProgress(100)
            return self.result.returncode == 0
        except Exception as exc:
            self._capture_error(exc)
            return False


class UninstallTransformezTask(TransformezTask):
    """Uninstall Transformez from the managed isolated runtime."""

    def __init__(self) -> None:
        super().__init__("Uninstall Transformez from isolated runtime")
        self.result: subprocess.CompletedProcess[str] | None = None

    def run(self) -> bool:
        try:
            if self.isCanceled():
                return False

            if not runtime_exists():
                self.error = RuntimeError(
                    "The isolated Transformez runtime does not exist."
                )
                return False

            self.setProgress(10)
            self.result = self._run_process(runtime_uninstall_command())
            if self.result is None or self.isCanceled():
                return False

            if self.result.returncode != 0:
                self.error = RuntimeError(
                    (self.stderr or self.stdout or "pip uninstall failed").strip()
                )
                return False

            self.setProgress(100)
            return True
        except Exception as exc:
            self._capture_error(exc)
            return False


class BuildShiftGridTask(TransformezTask):
    """Run Transformez in the isolated runtime and write a shift grid."""

    def __init__(
        self,
        *,
        region: list[float],
        increment: str,
        source_reference: str,
        target_reference: str,
        output_path: str | Path,
        use_stations: bool = False,
    ):
        super().__init__(
            f"Build Transformez shift grid: {source_reference} -> {target_reference}"
        )
        self.region = list(region)
        self.increment = increment
        self.source_reference = source_reference
        self.target_reference = target_reference
        self.output_path = Path(output_path)
        self.use_stations = use_stations
        self.written_path: Path | None = None
        self.worker_payload: dict | None = None
        self.status_message: str = "Starting Transformez"

    def _handle_stdout_line(self, line: str) -> None:
        if not line.strip():
            return

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return

        message_type = payload.get("type")

        if message_type == "progress":
            try:
                progress = float(payload.get("progress", 0.0))
            except (TypeError, ValueError):
                progress = 0.0
            self.setProgress(max(0.0, min(100.0, progress)))
            self.status_message = str(
                payload.get("message") or payload.get("stage") or ""
            )
            return

        if message_type in {"result", "error"} or "ok" in payload:
            self.worker_payload = payload

    def run(self) -> bool:
        if self.isCanceled():
            return False

        try:
            request = {
                "operation": "build_shift_grid",
                "region": self.region,
                "increment": self.increment,
                "source_reference": self.source_reference,
                "target_reference": self.target_reference,
                "output_path": str(self.output_path),
                "use_stations": self.use_stations,
            }

            worker = PLUGIN_DIR / "runtime_worker.py"
            self.setProgress(1)
            result = self._run_process(
                [str(runtime_python()), "-u", str(worker)],
                input_text=json.dumps(request),
            )
            if result is None:
                return False
            if self.isCanceled():
                return False

            payload = self.worker_payload
            if payload is None:
                # Backward compatibility with a worker that only emits one final JSON line.
                for line in reversed(self.stdout.splitlines()):
                    if not line.strip():
                        continue
                    try:
                        candidate = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if "ok" in candidate or candidate.get("type") in {
                        "result",
                        "error",
                    }:
                        payload = candidate
                        break

            self.worker_payload = payload

            ok = bool(payload and payload.get("ok"))
            if result.returncode != 0 or not ok:
                if payload is not None:
                    self.error = RuntimeError(
                        f"{payload.get('error_type', 'TransformezError')}: "
                        f"{payload.get('error', 'Shift-grid generation failed')}"
                    )
                    self.traceback_text = payload.get("traceback")
                else:
                    self.error = RuntimeError(
                        (
                            self.stderr
                            or self.stdout
                            or "Transformez subprocess failed"
                        ).strip()
                    )
                return False

            if payload is None:
                return False

            self.written_path = Path(payload["output_path"]).resolve()
            self.setProgress(100)
            return not self.isCanceled()
        except Exception as exc:
            self._capture_error(exc)
            return False
