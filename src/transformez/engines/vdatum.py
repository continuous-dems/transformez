#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.engines.vdatum
~~~~~~~~~~~~~~~~~~

Wrapper and installer for NOAA's VDatum Java transformation engine.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Literal

from fetchez.utils import remove_glob

logger = logging.getLogger(__name__)


InstallScope = Literal["user", "project"]
DEFAULT_VDATUM_VERSION = "4.8"
VDATUM_FULL_RELEASES = {
    "4.8": "20250917",
}


class VDatumInstallError(RuntimeError):
    """Raised when VDatum cannot be installed or resolved."""


def _clean_version(version: str) -> str:
    return version.removeprefix("v.").removeprefix("v")


def project_vdatum_dir(version: str = DEFAULT_VDATUM_VERSION) -> Path:
    """Return the project-local VDatum package directory."""

    return Path.cwd() / "transformez_cache" / "vdatum" / _clean_version(version)


def user_vdatum_dir(version: str = DEFAULT_VDATUM_VERSION) -> Path:
    """Return the per-user VDatum package directory."""

    clean_version = _clean_version(version)

    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return root / "transformez" / "vdatum" / clean_version

    return Path.home() / ".local" / "share" / "transformez" / "vdatum" / clean_version


def vdatum_install_dir(
    version: str = DEFAULT_VDATUM_VERSION,
    scope: InstallScope = "user",
) -> Path:
    """Return the install directory for a VDatum version and scope."""

    if scope == "project":
        return project_vdatum_dir(version)

    return user_vdatum_dir(version)


def _find_vdatum_jar(root: Path) -> Path | None:
    """Find vdatum.jar within a known VDatum package root."""

    direct_candidates = (
        root / "vdatum.jar",
        root / "vdatum" / "vdatum.jar",
        root / "VDatum.jar",
        root / "vdatum" / "VDatum.jar",
    )

    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate.resolve()

    if not root.is_dir():
        return None

    matches = sorted(
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path.name.casefold() == "vdatum.jar"
    )
    return matches[0] if matches else None


def resolve_vdatum_path(
    version: str = DEFAULT_VDATUM_VERSION,
) -> Path | None:
    """Resolve a VDatum JAR using deterministic Transformez precedence.

    Resolution order:
      1. project-local Transformez cache
      2. per-user Transformez data directory
      3. vdatum.jar available on PATH

    Arbitrary filesystem searches are intentionally avoided so an old,
    unrelated VDatum installation cannot silently win.
    """

    clean_version = _clean_version(version)

    candidates = (
        project_vdatum_dir(clean_version),
        user_vdatum_dir(clean_version),
    )

    for root in candidates:
        jar = _find_vdatum_jar(root)
        if jar is not None:
            return jar

    system = shutil.which("vdatum.jar")
    return Path(system).resolve() if system else None


def _java_available() -> bool:
    try:
        subprocess.run(
            ["java", "-version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    return True


class Vdatum:
    """Wrapper for NOAA's VDatum Java transformation engine.

    An supplied ``jar`` always wins. Otherwise the requested
    version is resolved using Transformez's project -> user -> PATH precedence.

    Attributes:
        jar: Path to vdatum.jar.
        version: Requested VDatum software version.
        ivert: Input vertical datum.
        overt: Output vertical datum.
        ihorz: Input horizontal datum.
        ohorz: Output horizontal datum.
        region: VDatum region grid number.
    """

    def __init__(
        self,
        jar: str | Path | None = None,
        version: str = DEFAULT_VDATUM_VERSION,
        ivert: str = "navd88:m:height",
        overt: str = "mhw:m:height",
        ihorz: str = "NAD83_2011:geo:deg",
        ohorz: str = "NAD83_2011:geo:deg",
        epoch_in: str | None = None,
        epoch_out: str | None = None,
        region: str = "4",
        fmt: str = "txt",
        xyzl: str = "0,1,2",
        skip: int = 0,
        delim: str = "space",
        result_dir: str = "result",
        verbose: bool = False,
    ):
        self.version = _clean_version(version)
        self.jar = Path(jar).expanduser().resolve() if jar is not None else None
        self.ivert = ivert
        self.overt = overt
        self.ihorz = ihorz
        self.ohorz = ohorz
        self.region = region
        self.fmt = fmt
        self.xyzl = xyzl
        self.skip = skip
        self.delim = delim
        self.result_dir = result_dir
        self.verbose = verbose
        self.epoch_in = epoch_in
        self.epoch_out = epoch_out

        if self.jar is None:
            self.jar = resolve_vdatum_path(self.version)

        if self.jar is None:
            logger.debug(
                "VDatum %s is not installed in a managed Transformez location "
                "or available on PATH. Run "
                "'transformez vdatum install --version %s'.",
                self.version,
                self.version,
            )
        else:
            logger.debug(
                "Using VDatum %s from %s",
                self.vdatum_get_version() or self.version,
                self.jar,
            )

        self.vdatum_set_horz()

    @property
    def has_vdatum(self) -> bool:
        return self.jar is not None and self.jar.is_file()

    @property
    def package_dir(self) -> Path | None:
        """Return the directory containing the selected VDatum JAR."""

        return self.jar.parent if self.jar is not None else None

    def vdatum_set_horz(self) -> None:
        if "ITRF" in self.overt:
            self.ohorz = self.overt
            self.epoch = "1997.0:1997.0"

    def vdatum_locate_jar(self) -> list[Path] | None:
        """Resolve and select the requested VDatum installation."""

        self.jar = resolve_vdatum_path(self.version)
        if self.jar is None:
            return None

        return [self.jar]

    def _run_java(
        self,
        args: list[str],
        *,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if self.jar is None:
            self.vdatum_locate_jar()

        if self.jar is None:
            raise VDatumInstallError(...)

        cmd = [
            "java",
            "-jar",
            str(self.jar),
            *args,
        ]

        logger.debug("Running VDatum: %s", " ".join(cmd))

        return subprocess.run(
            cmd,
            cwd=self.jar.parent,
            capture_output=True,
            text=True,
            check=check,
        )

    def __run_java(
        self,
        args: list[str],
        *,
        check: bool = False,
        headless: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run the selected VDatum package from its own package directory."""

        if self.jar is None:
            self.vdatum_locate_jar()

        if self.jar is None:
            raise VDatumInstallError(
                f"VDatum {self.version} is not installed. "
                f"Run 'transformez vdatum install --version {self.version}'."
            )
        # ["java", f"-Djava.awt.headless={str(headless).lower()}", "-jar", str(self.jar), *args],
        return subprocess.run(
            ["java", "-jar", str(self.jar), *args],
            cwd=self.jar.parent,
            capture_output=True,
            text=True,
            check=check,
        )

    def vdatum_get_version(self) -> str | None:
        """Return the version reported by the selected VDatum JAR."""

        if self.jar is None:
            self.vdatum_locate_jar()

        if self.jar is None:
            return None

        try:
            proc = self._run_java(["-"])
        except (OSError, VDatumInstallError):
            return None

        output = "\n".join((proc.stdout, proc.stderr))

        for line in output.splitlines():
            stripped = line.strip()
            lower = stripped.casefold()

            if "vdatum" not in lower:
                continue

            # Common VDatum forms contain "v4.x" or "- v4.x".
            for token in stripped.replace("(", " ").replace(")", " ").split():
                candidate = token.strip(",:;")
                if candidate.casefold().startswith("v") and any(
                    char.isdigit() for char in candidate
                ):
                    return candidate.removeprefix("v")

        return None

    def installation_info(self) -> dict[str, str | None]:
        """Describe the selected VDatum installation for diagnostics."""

        resolved = str(self.jar) if self.jar is not None else None
        reported = self.vdatum_get_version() if self.jar is not None else None

        source: str | None = None
        if self.jar is not None:
            try:
                self.jar.relative_to(project_vdatum_dir(self.version))
                source = "project"
            except ValueError:
                try:
                    self.jar.relative_to(user_vdatum_dir(self.version))
                    source = "user"
                except ValueError:
                    source = "system"

        return {
            "requested_version": self.version,
            "reported_version": reported,
            "path": resolved,
            "source": source,
        }

    def vdatum_help(self) -> str:
        proc = self._run_java(["-help"])
        return "\n".join(part for part in (proc.stdout, proc.stderr) if part)

    def vdatum_xyz(self, xyz: list[float]) -> list[float]:
        """Run VDatum on a single XYZ coordinate."""

        if self.jar is None:
            self.vdatum_locate_jar()

        if self.jar is None:
            return xyz

        args = [
            f"ihorz:{self.ihorz}",
            f"ivert:{self.ivert}",
            f"ohorz:{self.ohorz}",
            f"overt:{self.overt}",
            "-deg2dms",
            f"-pt:{xyz[0]},{xyz[1]},{xyz[2]}",
        ]

        if self.epoch_in is not None and self.epoch_out is not None:
            args.append(f"epoch:{self.epoch_in}:{self.epoch_out}")

        args.append(f"region:{self.region}")

        proc = self._run_java(args)

        if proc.returncode != 0:
            raise RuntimeError(
                f"VDatum point transformation failed:\n{proc.stderr or proc.stdout}"
            )

        for line in proc.stdout.splitlines():
            if "Height/Z" not in line:
                continue

            try:
                z = float(line.split()[2])
                return [xyz[0], xyz[1], z]
            except (ValueError, IndexError):
                continue

        raise RuntimeError(
            "Unable to parse VDatum point result.\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

    def vdatum_clean_result(self) -> None:
        """Clean the VDatum result directory."""

        remove_glob(f"{self.result_dir}/*")
        try:
            os.removedirs(self.result_dir)
        except OSError:
            pass

    def run_vdatum(self, src_fn: str | Path):
        """Run VDatum on an XYZ text file."""

        if self.jar is None:
            self.vdatum_locate_jar()

        if self.jar is None:
            return [], -1

        src_path = Path(src_fn).expanduser().resolve()
        result_path = Path(self.result_dir).expanduser().resolve()
        result_path.mkdir(parents=True, exist_ok=True)

        epoch_str = f"epoch:{self.epoch}" if self.epoch is not None else None

        args = [
            f"ihorz:{self.ihorz}",
            f"ivert:{self.ivert}",
            f"ohorz:{self.ohorz}",
            f"overt:{self.overt}",
            "-nodata",
            (
                f"-file:txt:{self.delim},{self.xyzl},skip{self.skip}:"
                f"{src_path}:{result_path}"
            ),
        ]

        if epoch_str is not None:
            args.append(epoch_str)

        args.append(f"region:{self.region}")

        proc = self._run_java(args)
        return proc.stdout, proc.returncode


def _normalize_vdatum_grid_case(root: Path) -> None:
    """Add case aliases required by VDatum on case-sensitive filesystems."""

    if sys.platform == "win32":
        return

    for source in root.rglob("*.gtx"):
        alias = source.with_name(f"{source.stem.upper()}{source.suffix}")

        if alias == source or alias.exists():
            continue

        alias.symlink_to(source.name)

        logger.debug(
            "Added VDatum case-sensitive grid alias: %s -> %s",
            alias.name,
            source.name,
        )


def install_vdatum_package(
    version: str = DEFAULT_VDATUM_VERSION,
    scope: InstallScope = "user",
) -> Path:
    """Download and install a versioned NOAA VDatum package.

    The complete VDatum package is retained because the JAR and its supporting
    transformation data form one executable engine installation.

    Args:
        version: NOAA VDatum software version.
        scope: ``"user"`` for the Transformez user data directory or
            ``"project"`` for ``./transformez_cache``.

    Returns:
        Path to the installed ``vdatum.jar``.
    """

    clean_version = _clean_version(version)

    if not _java_available():
        raise VDatumInstallError(
            "Java is required to run NOAA VDatum but was not found in PATH."
        )

    target_dir = vdatum_install_dir(clean_version, scope)

    existing = _find_vdatum_jar(target_dir)
    if existing is not None:
        logger.info(
            "VDatum %s is already installed at %s",
            clean_version,
            existing,
        )
        return existing

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    release = VDATUM_FULL_RELEASES.get(clean_version)

    if release is None:
        raise VDatumInstallError(
            f"No full-package release is defined for VDatum {clean_version}."
        )

    url = f"https://vdatum.noaa.gov/download/data/vdatum_all_{release}.zip"

    with tempfile.TemporaryDirectory(prefix="transformez-vdatum-") as tmpdir:
        tmp_path = Path(tmpdir)
        zip_path = tmp_path / f"vdatum_v{clean_version}.zip"
        extract_dir = tmp_path / "extract"

        logger.info(
            "Downloading VDatum %s from %s. "
            "The NOAA VDatum package is large and includes supporting data.",
            clean_version,
            url,
        )
        urllib.request.urlretrieve(url, zip_path)

        logger.info("Extracting VDatum %s...", clean_version)
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)

        jar = _find_vdatum_jar(extract_dir)
        if jar is None:
            raise VDatumInstallError(
                f"VDatum {clean_version} archive contains no vdatum.jar."
            )

        if target_dir.exists():
            shutil.rmtree(target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)

        extracted_items = list(extract_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            source_root = extracted_items[0]
            for item in source_root.iterdir():
                shutil.move(str(item), target_dir / item.name)
        else:
            for item in extracted_items:
                shutil.move(str(item), target_dir / item.name)

    installed = _find_vdatum_jar(target_dir)
    if installed is None:
        raise VDatumInstallError(
            f"VDatum {clean_version} installation completed but "
            "vdatum.jar could not be resolved."
        )

    # VDatum 4.8 references xGEOID component filenames using uppercase
    # region identifiers (e.g. CONUSPAC.gtx), while NOAA's distributed
    # archive contains lowercase filenames. Create aliases on
    # case-sensitive filesystems so the Java engine can resolve them.
    _normalize_vdatum_grid_case(target_dir)

    logger.info(
        "VDatum %s installed successfully at %s",
        clean_version,
        installed,
    )

    return installed


install_vdatum_jar = install_vdatum_package
