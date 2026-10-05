#!/usr/bin/env python

"""
transformez.progress
~~~~~~~~~~~~~~~

"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    progress: float
    stage: str
    message: str
    operation: int | None = None
    operation_count: int | None = None


ProgressCallback = Callable[[ProgressEvent], None]


def report_progress(
    callback: ProgressCallback | None,
    progress: float,
    stage: str,
    message: str = "",
) -> None:
    if callback is not None:
        callback(
            ProgressEvent(
                progress=max(0.0, min(100.0, progress)),
                stage=stage,
                message=message,
            )
        )
