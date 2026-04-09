#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.cli
~~~~~~~~~~~~~~~

The command-line interface for Transformez.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import click
import logging
from transformez import api

# logger = logging.getLogger(__name__)


class AliasedGroup(click.Group):
    """A custom Click Group that handles deprecated aliases."""

    def get_command(self, ctx, cmd_name):
        if cmd_name == "run":
            click.secho(
                " DEPRECATION WARNING: 'transformez run' is deprecated and will be removed in a future release.\n"
                "Please use 'transformez grid' to generate shift grids instead.",
                fg="yellow",
                err=True,
            )
            return click.Group.get_command(self, ctx, "run")

        return click.Group.get_command(self, ctx, cmd_name)


@click.group(name="transform", cls=AliasedGroup)
@click.version_option(package_name="transformez")
def transformez_cli():
    """Apply vertical datum transformations and generate shift grids."""

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    pass


@transformez_cli.command("run")
@click.argument("input_file", required=False)
@click.option(
    "-R", "--region", help="Bounding box or location string (if no input file)."
)
@click.option(
    "-E", "--increment", help="Resolution (e.g., 1s, 30m) (if no input file)."
)
@click.option(
    "-I", "--input-datum", required=True, help="Source Datum (e.g., 'mllw', '5703')."
)
@click.option(
    "-O",
    "--output-datum",
    required=True,
    help="Target Datum (e.g., '4979', '5703:g2012b').",
)
@click.option("--out", "-o", help="Output filename (default: auto-named).")
@click.option(
    "--decay-pixels",
    type=int,
    default=100,
    help="Number of pixels to decay tidal shifts inland.",
)
@click.option("--preview", is_flag=True, help="Preview the transformation output.")
def transform_run(
    input_file, region, increment, input_datum, output_datum, out, decay_pixels, preview
):
    """Transform a raster's vertical datum or generate a standalone shift grid.

    If an INPUT_FILE is provided, that specific raster is transformed in place.
    If no INPUT_FILE is provided, -R and -E must be used to generate a shift grid.

    Examples:\n
      Transform a DEM : transformez run my_dem.tif -I mllw -O 5703
      Generate a Grid : transformez run -R loc:"Miami" -E 1s -I mllw -O 4979
    """

    if input_file:
        click.secho(f"Transforming raster: {input_file}", fg="cyan", bold=True)
        click.echo(f"   Shift: {input_datum} ➔ {output_datum}")

        result = api.transform_raster(
            input_raster=input_file,
            datum_in=input_datum,
            datum_out=output_datum,
            decay_pixels=decay_pixels,
            output_raster=out,
            verbose=True,
        )

        if result:
            click.secho(
                f"Successfully transformed raster: {result}", fg="green", bold=True
            )
        else:
            click.secho("Failed to transform raster.", fg="red")
            sys.exit(1)

    elif region and increment:
        click.secho(
            f"Generating vertical shift grid for region: {region}...",
            fg="cyan",
            bold=True,
        )
        click.echo(f"   Shift: {input_datum} ➔ {output_datum} @ {increment}")

        # Auto-generate an output name if one wasn't provided
        out_fn = out or f"shift_{input_datum}_to_{output_datum.replace(':', '_')}.tif"

        result = api.generate_grid(
            region=region,
            increment=increment,
            datum_in=input_datum,
            datum_out=output_datum,
            decay_pixels=decay_pixels,
            out_fn=out_fn,
            verbose=True,
        )

        if preview:
            api.plot_grid(result, region)

        if result is not None:
            click.secho(
                f"Successfully generated shift grid: {out_fn}", fg="green", bold=True
            )
        else:
            click.secho("Failed to generate shift grid.", fg="red")
            sys.exit(1)

    else:
        click.secho(
            "Error: You must provide either an INPUT_FILE or both --region and --increment.",
            fg="red",
        )
        sys.exit(1)


# =====================================================================
# GENERATE SHIFT GRID
# =====================================================================
@transformez_cli.command("grid")
@click.option("-R", "--region", required=True, help="Bounding box or location string.")
@click.option("-E", "--increment", required=True, help="Resolution (e.g., 1s, 30m).")
@click.option(
    "-I", "--input-datum", required=True, help="Source Datum (e.g., 'mllw', '5703')."
)
@click.option(
    "-O",
    "--output-datum",
    required=True,
    help="Target Datum (e.g., '4979', '5703:g2012b').",
)
@click.option("--out", "-o", help="Output filename (default: auto-named).")
@click.option(
    "--decay-pixels", type=int, default=100, help="Pixels to decay tidal shifts inland."
)
@click.option(
    "--preview", is_flag=True, help="Show matplotlib preview instead of saving."
)
def transform_grid(
    region, increment, input_datum, output_datum, out, decay_pixels, preview
):
    """Generate a standalone vertical shift grid for a specified region."""

    click.secho(
        f"Generating vertical shift grid for region: {region}...",
        fg="cyan",
        bold=True,
    )
    click.echo(f"   Shift: {input_datum} ➔ {output_datum} @ {increment}")

    # Auto-generate an output name if one wasn't provided
    out_fn = out or f"shift_{input_datum}_to_{output_datum.replace(':', '_')}.tif"

    result = api.generate_grid(
        region=region,
        increment=increment,
        datum_in=input_datum,
        datum_out=output_datum,
        decay_pixels=decay_pixels,
        out_fn=out_fn,
        verbose=True,
    )

    if preview:
        api.plot_grid(result, region)

    if result is not None:
        click.secho(
            f"Successfully generated shift grid: {out_fn}", fg="green", bold=True
        )
    else:
        click.secho("Failed to generate shift grid.", fg="red")
        sys.exit(1)


# =====================================================================
# TRANSFORM EXISTING RASTER (DEM)
# =====================================================================
@transformez_cli.command("raster")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-I", "--input-datum", required=True, help="Source Datum (e.g., 'mllw').")
@click.option(
    "-O", "--output-datum", required=True, help="Target Datum (e.g., '5703:g2012b')."
)
@click.option(
    "--in-units",
    default="auto",
    type=click.Choice(["auto", "m", "ft", "us-ft"]),
    help="Z-units of the input DEM.",
)
@click.option(
    "--out-units",
    default="auto",
    type=click.Choice(["auto", "m", "ft", "us-ft"]),
    help="Desired Z-units for the output DEM.",
)
@click.option("--out", "-o", help="Output filename (default: auto-named).")
@click.option(
    "--decay-pixels", type=int, default=100, help="Pixels to decay tidal shifts inland."
)
def transform_raster(
    input_file, input_datum, output_datum, in_units, out_units, out, decay_pixels
):
    """Apply a vertical datum shift (and optional unit conversion) to an existing DEM."""

    click.secho(f"Transforming raster: {input_file}", fg="cyan", bold=True)
    click.echo(f"   Shift: {input_datum} ➔ {output_datum}")

    result = api.transform_raster(
        input_raster=input_file,
        datum_in=input_datum,
        datum_out=output_datum,
        decay_pixels=decay_pixels,
        output_raster=out,
        z_unit_in=in_units,
        z_unit_out=out_units,
        verbose=True,
    )

    if result:
        click.secho(f"Successfully transformed raster: {result}", fg="green", bold=True)
    else:
        click.secho("Failed to transform raster.", fg="red")
        sys.exit(1)


@transformez_cli.command("list")
def transform_list():
    """List all supported vertical datums, EPSG codes, and geoids."""
    try:
        from transformez.definitions import Datums

        click.secho("\n🌊 Supported Tidal Surfaces:", fg="cyan", bold=True)
        # For tidal datums, the user types the dictionary key (e.g., 'mllw')
        for key, v in Datums.SURFACES.items():
            region_str = v.get("region", "global").upper()
            click.echo(f"  {key:<12} : {v.get('name', key):<30} [{region_str}]")

        click.secho("\n🌐 Ellipsoidal / Frame Datums (EPSG):", fg="cyan", bold=True)
        # For ellipsoidal, explicitly list the EPSG codes
        click.echo(f"  {'4979':<12} : WGS84 - World Geodetic System 1984")
        click.echo(f"  {'6319':<12} : NAD83 - North American Datum 1983")

        click.secho("\n🏔️  Orthometric / Geoid-Based (EPSG):", fg="cyan", bold=True)
        # For orthometric, the key in Datums.CDN is typically the EPSG code (e.g., '5703')
        for epsg_key, v in Datums.CDN.items():
            # Fallback to the key if 'epsg' isn't explicitly defined in the dict
            epsg_code = v.get("epsg", epsg_key)
            geoid_str = v.get("default_geoid", "None")
            click.echo(
                f"  {str(epsg_code):<12} : {v.get('name', 'Unknown'):<30} (Default Geoid: {geoid_str})"
            )

        click.secho("\n🌍 Available Geoids:", fg="cyan", bold=True)
        click.echo(f"  {', '.join(Datums.GEOIDS.keys())}")

        click.secho("\n💡 Pro-Tip:", fg="yellow", bold=True, nl=False)
        click.echo(
            " Combine an EPSG and a specific Geoid using a colon (e.g., -O 5703:g2012b)\n"
        )

    except ImportError:
        click.secho("Error: Could not load Transformez datum definitions.", fg="red")


# --- HTDP CLI GROUP ---
@transformez_cli.group("htdp")
def htdp_group():
    """Manage and run NGS HTDP (Horizontal Time-Dependent Positioning)."""

    pass


@htdp_group.command("install")
def install_htdp():
    """Downloads and compiles the HTDP executable."""

    from transformez.htdp import install_htdp_binary

    install_htdp_binary()


# --- VDATUM CLI GROUP ---
@transformez_cli.group("vdatum")
def vdatum_group():
    """Manage and run the NOAA VDatum Java engine."""

    pass


@vdatum_group.command("install")
def install_vdatum():
    """Downloads and extracts the local VDatum software."""

    from transformez.vdatum import install_vdatum_jar

    install_vdatum_jar()


@vdatum_group.command("run")
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
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
def run_vdatum_cli(
    input_file, output_file, in_datum, out_datum, in_unit, out_unit, region
):
    """Process an XYZ text file through the local VDatum Java engine."""

    from transformez.vdatum import Vdatum

    vd = Vdatum(
        ivert=f"{in_datum}:{in_unit}:height",
        overt=f"{out_datum}:{out_unit}:height",
        region=region,
    ).run_vdatum(input_file)


@vdatum_group.command("list")
def vdatum_list():
    """List the supported vdatum grids"""

    from transformez.vdatum import Vdatum

    vd = Vdatum().vdatum_help()
    click.echo(vd)


if __name__ == "__main__":
    transformez_cli()
