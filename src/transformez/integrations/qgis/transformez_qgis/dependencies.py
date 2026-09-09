#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.integrations.qgis.dependencies
~~~~~~~~~~~~~~~

Isolated runtime management for the Transformez QGIS plugin.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from qgis.core import QgsApplication


PLUGIN_DIR = Path(__file__).resolve().parent
PROFILE_DIR = Path(QgsApplication.qgisSettingsDirPath()).resolve()
RUNTIME_ROOT = PROFILE_DIR / "transformez"
RUNTIME_DIR = RUNTIME_ROOT / "runtime"
LEGACY_RUNTIME_DIR = PLUGIN_DIR / "runtime"

RUNTIME_PYTHON = RUNTIME_DIR / "bin" / "python"
if sys.platform == "win32":
    RUNTIME_PYTHON = RUNTIME_DIR / "Scripts" / "python.exe"


def runtime_python() -> Path:
    return RUNTIME_PYTHON


def runtime_exists() -> bool:
    return RUNTIME_PYTHON.exists()


def legacy_runtime_exists() -> bool:
    return LEGACY_RUNTIME_DIR.exists()


def cleanup_legacy_runtime() -> tuple[bool, str | None]:
    """Remove the obsolete in-plugin runtime after the external runtime is ready."""

    if not LEGACY_RUNTIME_DIR.exists():
        return True, None

    try:
        shutil.rmtree(LEGACY_RUNTIME_DIR)
    except Exception as exc:
        return False, str(exc)

    return True, None


def runtime_probe() -> tuple[bool, str | None]:
    """Check whether the isolated runtime can import Transformez."""

    if not runtime_exists():
        if legacy_runtime_exists():
            return (
                False,
                "The plugin runtime location has changed. Reinstall Transformez once "
                "to create the external runtime; the old in-plugin runtime will then be removed.",
            )
        return False, "Isolated Transformez runtime has not been created yet."

    code = (
        "import json, transformez; "
        "print(json.dumps({'version': getattr(transformez, '__version__', None)}))"
    )
    result = subprocess.run(
        [str(RUNTIME_PYTHON), "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Transformez import failed").strip()
        return False, detail

    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        return True, result.stdout.strip() or None

    version = payload.get("version")
    return True, str(version) if version else None


def runtime_create_command() -> list[str]:
    """Return the command used to create the isolated virtual environment."""

    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    return [sys.executable, "-m", "venv", str(RUNTIME_DIR)]


def runtime_uninstall_command() -> list[str]:
    """Return the pip command used to uninstall Transformez from the runtime."""

    return [
        str(RUNTIME_PYTHON),
        "-m",
        "pip",
        "uninstall",
        "-y",
        "transformez",
    ]


def runtime_install_command(source: str | Path | None = None) -> list[str]:
    """Return the pip command used to install Transformez into the runtime."""

    package = str(Path(source).expanduser().resolve()) if source else "transformez"
    return [
        str(RUNTIME_PYTHON),
        "-m",
        "pip",
        "install",
        "--upgrade",
        package,
    ]
