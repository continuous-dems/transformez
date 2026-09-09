#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.integrations.qgis.runtime_worker
~~~~~~~~~~~~~~~

Subprocess worker for Transformez operations.

This file is executed by the plugin-owned isolated Python runtime, not by QGIS.
Communication with the plugin is newline-delimited JSON over stdout. Normal
Transformez logging remains on stderr and is drained independently by QgsTask.

The QGIS integration deliberately targets Transformez's public API. Reference
parsing, VDatum coverage selection, xGEOID normalization, mosaicing, and output
provenance remain responsibilities of Transformez itself rather than the plugin.
"""

from __future__ import annotations

import inspect
import json
import sys
import traceback
from pathlib import Path


def emit(payload: dict) -> None:
    print(json.dumps(payload), flush=True)


def emit_progress(event=None, *args, **kwargs) -> None:
    """Adapt common Transformez progress callback shapes to worker JSONL."""

    progress = kwargs.get("progress")
    stage = kwargs.get("stage", "")
    message = kwargs.get("message", "")

    if event is not None:
        if isinstance(event, dict):
            progress = event.get("progress", progress)
            stage = event.get("stage", stage)
            message = event.get("message", message)
        elif isinstance(event, (int, float)):
            progress = event
        else:
            progress = getattr(event, "progress", progress)
            stage = getattr(event, "stage", stage)
            message = getattr(event, "message", message)

    if progress is None and args:
        progress = args[0]
    if not stage and len(args) > 1:
        stage = args[1]
    if not message and len(args) > 2:
        message = args[2]

    try:
        progress_value = float(progress if progress is not None else 0.0)
    except (TypeError, ValueError):
        progress_value = 0.0

    emit(
        {
            "type": "progress",
            "progress": max(0.0, min(100.0, progress_value)),
            "stage": str(stage or ""),
            "message": str(message or stage or ""),
        }
    )


def _supported_kwargs(function, values: dict) -> dict:
    """Return only keyword arguments accepted by ``function``.

    This keeps the plugin compatible across nearby Transformez releases while
    still preferring the current public API. If a callable accepts ``**kwargs``,
    all values are retained.
    """

    signature = inspect.signature(function)
    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return values

    return {key: value for key, value in values.items() if key in signature.parameters}


def _build_with_public_api(request: dict, output: Path) -> Path:
    """Build and write a shift grid using ``transformez.api.generate_grid``."""

    from transformez.api import generate_grid

    kwargs = {
        "region": request["region"],
        "increment": request["increment"],
        "datum_in": request["source_reference"],
        "datum_out": request["target_reference"],
        "out_fn": output,
        "use_stations": bool(request.get("use_stations", False)),
        "verbose": True,
        "progress_callback": emit_progress,
    }

    emit_progress(
        progress=2,
        stage="planning",
        message="Resolving Transformez references",
    )

    result = generate_grid(**_supported_kwargs(generate_grid, kwargs))

    # Current generate_grid writes through out_fn and returns the shift array.
    # Be tolerant of future/older public APIs that instead return a ShiftGrid.
    if result is not None and not output.exists() and hasattr(result, "write"):
        emit_progress(progress=95, stage="writing", message="Writing shift grid")
        written = result.write(output)
        if written is not None:
            output = Path(written).expanduser().resolve()

    if not output.exists():
        raise RuntimeError(
            "Transformez generate_grid completed without producing the requested output file."
        )

    return output.resolve()


def _build_with_legacy_internal_api(request: dict, output: Path) -> Path:
    """Compatibility path for older Transformez installations.

    New plugin/runtime installs should use the public API above. This path exists
    only so an already-managed older runtime does not fail solely because its
    public API predates ``out_fn`` support.
    """

    from transformez.grid.shift import build_shift_grid

    kwargs = {
        "region": request["region"],
        "increment": request["increment"],
        "datum_in": request["source_reference"],
        "datum_out": request["target_reference"],
        "use_stations": bool(request.get("use_stations", False)),
        "verbose": True,
        "progress_callback": emit_progress,
    }

    emit_progress(progress=1, stage="starting", message="Starting Transformez")
    shift_grid = build_shift_grid(**_supported_kwargs(build_shift_grid, kwargs))

    emit_progress(progress=95, stage="writing", message="Writing shift grid")
    written = shift_grid.write(output)
    return Path(written or output).expanduser().resolve()


def main() -> int:
    try:
        request = json.load(sys.stdin)
        operation = request.get("operation")

        if operation != "build_shift_grid":
            raise ValueError(f"Unsupported operation: {operation!r}")

        output = Path(request["output_path"]).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            written = _build_with_public_api(request, output)
        except (ImportError, AttributeError, TypeError) as public_api_error:
            # Keep nearby older Transformez releases usable, but make the
            # compatibility decision visible in the Transformez log.
            print(
                "[ WARNING ] qgis: Public Transformez API unavailable or incompatible; "
                f"using legacy builder ({public_api_error})",
                file=sys.stderr,
                flush=True,
            )
            written = _build_with_legacy_internal_api(request, output)

        emit_progress(progress=100, stage="complete", message="Shift grid complete")
        emit({"type": "result", "ok": True, "output_path": str(written)})
        return 0
    except Exception as exc:
        emit(
            {
                "type": "error",
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
