#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.cli.vdatum
~~~~~~~~~~~~~~~

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import click
from pathlib import Path

from typing import Literal
from fetchez.utils import FetchezMainGroup, FetchezMainCommand
from transformez.engines.vdatum import (
    DEFAULT_VDATUM_VERSION,
    Vdatum,
    install_vdatum_jar,
)


# --- VDATUM CLI GROUP ---
@click.group(
    cls=FetchezMainGroup,
    name="vdatum",
    fetchez_commands=["install", "run", "launch", "info", "help"],
)
def vdatum_group() -> None:
    """Manage the NOAA VDatum transformation engine."""

    pass


@vdatum_group.command("install")
@click.option(
    "--version",
    default=DEFAULT_VDATUM_VERSION,
    show_default=True,
    help="VDatum software version to install.",
)
@click.option(
    "--scope",
    type=click.Choice(["user", "project"]),
    default="user",
    show_default=True,
    help="Installation scope.",
)
def install_vdatum(
    version: str,
    scope: Literal["user", "project"],
) -> None:
    """Download and install the NOAA VDatum software and data."""

    jar = install_vdatum_jar(
        version=version,
        scope=scope,
    )

    click.echo(f"VDatum {version} installed:")
    click.echo(f"  {jar}")


@vdatum_group.command("run", cls=FetchezMainCommand)
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-I", "--in-datum", required=True, help="VDatum input datum string (e.g., 'navd88')"
)
@click.option(
    "-O",
    "--out-datum",
    required=True,
    help="VDatum output datum string (e.g., 'nad83_2011')",
)
@click.option("--in-unit", default="m", help="Input units (m, ft, us-ft)")
@click.option("--out-unit", default="m", help="Output units (m, ft, us-ft)")
@click.option("--region", default="4", help="VDatum region grid")
@click.option(
    "--version",
    default=DEFAULT_VDATUM_VERSION,
    show_default=True,
    help="VDatum engine version to use.",
)
def run_vdatum_cli(
    input_file: str,
    in_datum: str,
    out_datum: str,
    in_unit: str,
    out_unit: str,
    region: str,
    version: str,
) -> None:
    """Transform an XYZ file using the local NOAA VDatum engine."""

    vd = Vdatum(
        version=version,
        ivert=f"{in_datum}:{in_unit}:height",
        overt=f"{out_datum}:{out_unit}:height",
        region=region,
    )

    info = vd.installation_info()

    click.echo(
        f"Using VDatum {info['reported_version'] or version} from {info['path']}",
        err=True,
    )

    vd.run_vdatum(input_file)


@vdatum_group.command("help", cls=FetchezMainCommand)
def vdatum_help() -> None:
    """Show information reported by the installed VDatum engine."""

    vd = Vdatum().vdatum_help()
    click.echo(vd)


@vdatum_group.command("info")
@click.option(
    "--version",
    default=DEFAULT_VDATUM_VERSION,
    show_default=True,
)
def vdatum_info(version: str) -> None:
    """Show the VDatum installation selected by Transformez."""

    vd = Vdatum(version=version)
    info = vd.installation_info()

    if info["path"] is None:
        raise click.ClickException(f"VDatum {version} is not installed.")

    click.echo("VDatum engine")
    click.echo("")
    click.echo(f"Requested version: {info['requested_version']}")
    click.echo(f"Reported version:  {info['reported_version'] or 'Unknown'}")
    click.echo(f"Source:            {info['source'] or 'Unknown'}")
    click.echo(f"Path:              {info['path']}")


@vdatum_group.command("launch", cls=FetchezMainCommand)
def vdatum_launch() -> None:
    """Launch the VDatum engine."""

    vd = Vdatum()

    vd._run_java([])
