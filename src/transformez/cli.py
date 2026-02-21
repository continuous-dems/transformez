#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.cli
~~~~~~~~~~~~~~~

The command-line interface for Transformez.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import sys
import argparse
import logging
import rasterio

from . import __version__
from .transform import VerticalTransform
from .definitions import Datums
from .grid_engine import plot_grid, GridWriter, GridEngine
from .htdp import HAS_HTDP

from fetchez import spatial
from fetchez import utils
from fetchez.spatial import parse_region

logging.basicConfig(level=logging.INFO, format="[ %(levelname)s ] %(message)s", stream=sys.stderr)
logger = logging.getLogger("transformez")
logging.getLogger("fetchez").setLevel(logging.WARNING)


def parse_compound_datum(datum_arg):
    """Parse string 'EPSG:GEOID' or 'NAME'."""
    if not datum_arg: return None, None
    s = str(datum_arg)
    if ':' in s:
        parts = s.split(':')
        # Handle "5703:geoid=g2012b" or "5703:g2012b"
        geoid_part = parts[1]
        if 'geoid=' in geoid_part:
            geoid = geoid_part.split('=')[1]
        else:
            geoid = geoid_part
        return Datums.get_vdatum_by_name(parts[0]), geoid
    else:
        return Datums.get_vdatum_by_name(s), None


def list_supported_datums():
    """Pretty print supported datums."""
    print(f"\nTransformez v{__version__} - Supported Datums\n")

    print("--- Tidal Surfaces (Local & Global) ---")
    for k, v in Datums.SURFACES.items():
        region = v.get("region", "global").upper()
        print(f"  {v['name']:<10} : {v['description']} [{region}]")

    print("\n--- Ellipsoidal / Frame (HTDP) ---")
    print(f"  {'NAD83':<10} : North American Datum 1983 (EPSG:6319)")
    print(f"  {'WGS84':<10} : World Geodetic System 1984 (EPSG:4979)")

    print("\n--- Orthometric / Geoid-Based ---")
    for k, v in Datums.CDN.items():
        print(f"  {v['name']:<20} (Default Geoid: {v.get('default_geoid', 'None')})")

    print("\n--- Available Geoids ---")
    print(f"  {', '.join(Datums.GEOIDS.keys())}")
    print("\n")


def transformez_cli():
    parser = argparse.ArgumentParser(
        description=f"{utils.CYAN}%(prog)s{utils.RESET} ({__version__}) :: Global Vertical Datum Transformer",
        epilog="Examples:\n"
               "  transformez -R -166/-164/63/64 -I mllw -O 4979\n"
               "  transformez input_dem.tif -I mllw -O 5703:geoid=g2012b",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input_file', nargs='?', help="Input DEM (GeoTIFF) to transform.")

    grp_loc = parser.add_argument_group('Location & Resolution (if no input file)')
    grp_loc.add_argument('-R', '--region', nargs='?', help='Region (West/East/South/North).')
    grp_loc.add_argument('-E', '--increment', nargs='?', help='Resolution (e.g. 1s, 0.0001).')

    grp_dat = parser.add_argument_group('Vertical Datums')
    grp_dat.add_argument('-I', '--input-datum', '--vdatum-in',
                         help='Source Datum (e.g. "mllw", "5703", "4979").')
    grp_dat.add_argument('-O', '--output-datum', '--vdatum-out',
                         help='Target Datum (e.g. "5703:geoid=g2012b", "4979").')

    grp_out = parser.add_argument_group('Output')
    grp_out.add_argument('-o', '--output', help='Output filename (default: auto-named).')
    grp_out.add_argument('--preview', action='store_true', help='Show plot of shift grid before saving.')

    grp_sys = parser.add_argument_group('System')
    grp_sys.add_argument('--list-datums', action='store_true', help='List supported datums.')
    grp_sys.add_argument('--cache-dir', help='Override cache directory.')
    grp_sys.add_argument('--verbose', action='store_true', help='Enable debug logging.')
    grp_sys.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    if args.list_datums:
        list_supported_datums()
        sys.exit(0)

    # Validation & Setup
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('fetchez').setLevel(logging.INFO)

    if not HAS_HTDP:
        logger.warning("HTDP tool not found in PATH. Frame transformations (NAD83<>WGS84) will be inaccurate.")

    cache_dir = args.cache_dir or os.path.join(os.path.expanduser('~'), '.transformez')
    if not os.path.exists(cache_dir): os.makedirs(cache_dir)

    # Parse Datums
    epsg_in, geoid_in = parse_compound_datum(args.input_datum)
    epsg_out, geoid_out = parse_compound_datum(args.output_datum)

    if not epsg_in or not epsg_out:
        parser.print_help()
        logger.error("Invalid datum specified. Use --list-datums to see options.")
        sys.exit(1)

    # Mode Selection (DEM vs Grid)
    target_dem = args.input_file

    if target_dem:
        # MODE A: Transform DEM
        if not os.path.exists(target_dem):
            parser.print_help()
            logger.error(f"Input file not found: {target_dem}")
            sys.exit(1)

        logger.info(f"Reading bounds from: {target_dem}")
        with rasterio.open(target_dem) as src:
            bounds = src.bounds
            region_obj = spatial.Region(bounds.left, bounds.right, bounds.bottom, bounds.top)
            nx, ny = src.width, src.height

        if not args.output:
            base, ext = os.path.splitext(target_dem)
            dst_fn = f"{base}_trans_{args.output_datum.replace(':','_')}{ext}"
        else:
            dst_fn = args.output

    elif args.region:
        # MODE B: Generate Grid
        if not args.increment:
            parser.print_help()
            logger.error("Increment (-E) is required when generating a grid from scratch.")
            sys.exit(1)

        regions = parse_region(args.region)
        region_obj = regions[0]

        # Parse Increment
        try:
            inc_val = utils.str2inc(args.increment)
            nx = int(region_obj.width / inc_val)
            ny = int(region_obj.height / inc_val)
        except:
            parser.print_help()
            logger.error(f"Invalid increment: {args.increment}")
            sys.exit(1)

        if not args.output:
            dst_fn = f"shift_{args.input_datum}_to_{args.output_datum.replace(':','_')}.tif"
        else:
            dst_fn = args.output

    else:
        parser.print_help()
        logger.error("Either an input file OR a region (-R) is required.")
        sys.exit(1)

    vt = VerticalTransform(
        region=region_obj,
        nx=nx, ny=ny,
        epsg_in=epsg_in, epsg_out=epsg_out,
        geoid_in=geoid_in, geoid_out=geoid_out,
        cache_dir=cache_dir,
        verbose=args.verbose
    )

    logger.info(f"Computing Shift: {args.input_datum} -> {args.output_datum}")
    shift_array, _ = vt._vertical_transform(vt.epsg_in, vt.epsg_out)

    if shift_array is None:
        logger.error("Transformation failed (No coverage found).")
        sys.exit(1)

    if args.preview:
        plot_grid(shift_array, region_obj, title=f"{args.input_datum} -> {args.output_datum}")

    if target_dem:
        logger.info(f"Applying shift to raster...")
        GridEngine.apply_vertical_shift(target_dem, shift_array, dst_fn)
    else:
        logger.info(f"Writing shift grid...")
        GridWriter.write(dst_fn, shift_array, region_obj)

    logger.info(f"Success: {dst_fn}")

if __name__ == '__main__':
    transformez_cli()
