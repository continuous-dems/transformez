#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.api
~~~~~~~~~~~~~~~
High-level Python Interface for Transformez.

Usage:
    import transformez

    # Generate a shift grid (returns a numpy array)
    shift_array = transformez.generate_grid(
        region=[-90, -89, 29, 30],
        increment="3s",
        datum_in="mllw",
        datum_out="5703"
    )

    # Transform an existing DEM directly
    out_file = transformez.transform_raster(
        input_raster="my_dem_mllw.tif",
        datum_in="mllw",
        datum_out="5703:g2012b",
        output_raster="my_dem_navd88.tif"
    )
"""

import os
import logging
import numpy as np
from typing import List, Union, Optional, Tuple

from .transform import VerticalTransform
from .definitions import Datums
from .grid_engine import GridWriter, GridEngine
from fetchez.spatial import parse_region, Region
from fetchez import utils

logger = logging.getLogger(__name__)


def _parse_datum(datum_arg: str) -> Tuple[Optional[int], Optional[str]]:
    """Helper to parse compound datum strings (e.g. '5703:g2012b')."""

    if not datum_arg:
        return None, None
    s = str(datum_arg)
    if ':' in s:
        parts = s.split(':')
        geoid_part = parts[1]
        geoid = (
            geoid_part.split('=')[1] if 'geoid=' in geoid_part else geoid_part
        )
        return Datums.get_vdatum_by_name(parts[0]), geoid
    return Datums.get_vdatum_by_name(s), None


def plot_grid(grid_array, region, title="Vertical Shift Preview"):
    """Plot the transformation grid using Matplotlib."""

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("Matplotlib is not installed. Cannot generate preview.")
        return

    if isinstance(region, Region):
        region_obj = region
    else:
        regions = parse_region(region)
        if not regions:
            logger.error(f"Could not parse region: {region}")
            return None
        region_obj = regions[0]

    masked_data = np.ma.masked_where(
        (np.isnan(grid_array)) | (grid_array == -9999) | (grid_array == 0),
        grid_array
    )

    if masked_data.count() == 0:
        logger.warning("Preview skipped: Grid contains no valid data.")
        return

    plt.figure(figsize=(10, 6))
    plot_region = [region_obj.xmin, region_obj.xmax, region_obj.ymin, region_obj.ymax]

    # im = plt.imshow(masked_data, extent=plot_region, cmap="RdBu_r", origin="upper")
    im = plt.imshow(masked_data, extent=plot_region, cmap="viridis", origin="upper")
    cbar = plt.colorbar(im)
    cbar.set_label("Vertical Shift (meters)")
    plt.title(title)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid(True, linestyle=':', alpha=0.6)

    stats = (f"Min: {masked_data.min():.3f} m\n"
             f"Max: {masked_data.max():.3f} m\n"
             f"Mean: {masked_data.mean():.3f} m")
    plt.annotate(stats, xy=(0.02, 0.02), xycoords='axes fraction',
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))
    logger.info("Displaying preview... Close the plot window to continue.")
    plt.show()


def generate_grid(
    region: Union[List[float], str, Region],
    increment: Union[str, float],
    datum_in: str,
    datum_out: str,
    decay_pixels: int = 100,
    out_fn: Optional[str] = None,
    cache_dir: Optional[str] = None,
    verbose: bool = False,
) -> Optional[np.ndarray]:
    """Generate a vertical shift grid for a specific region.

    Args:
        region: Bounds as [W, E, S, N], a 'loc:' string, or a Region object.
        increment: Resolution (e.g., '3s' or 0.0008333).
        datum_in: Source datum (e.g., 'mllw', '5703').
        datum_out: Target datum (e.g., '4979', '6319').
        decay_pixels: Set the pixel decay in case extrapolation is required.
        out_fn: If provided, saves the grid to this file (.tif or .gtx).
        cache_dir: Path to store downloaded grids.
        verbose: Enable debug logging.

    Returns:
        np.ndarray: The 2D vertical shift grid, or None if failed.
    """

    if isinstance(region, Region):
        region_obj = region
    else:
        regions = parse_region(region)
        if not regions:
            logger.error(f"Could not parse region: {region}")
            return None
        region_obj = regions[0]

    try:
        inc_val = utils.str2inc(str(increment))
        nx = int(region_obj.width / inc_val)
        ny = int(region_obj.height / inc_val)
    except Exception as e:
        logger.error(f"Invalid increment '{increment}': {e}")
        return None

    epsg_in, geoid_in = _parse_datum(datum_in)
    epsg_out, geoid_out = _parse_datum(datum_out)

    if not epsg_in or not epsg_out:
        logger.error(f"Invalid datum specified: {datum_in} -> {datum_out}")
        return None

    vt = VerticalTransform(
        region=region_obj,
        nx=nx, ny=ny,
        epsg_in=epsg_in, epsg_out=epsg_out,
        geoid_in=geoid_in, geoid_out=geoid_out,
        decay_pixels=decay_pixels,
        cache_dir=cache_dir,
        verbose=verbose
    )

    shift_array, _ = vt._vertical_transform(vt.epsg_in, vt.epsg_out)

    if shift_array is None:
        logger.error("Transformation failed to generate a grid.")
        return None

    if out_fn:
        GridWriter.write(out_fn, shift_array, region_obj)
        logger.info(f"Saved shift grid to {out_fn}")

    return shift_array


def transform_raster(
    input_raster: str,
    datum_in: str,
    datum_out: str,
    decay_pixels: int = 100,
    output_raster: Optional[str] = None,
    cache_dir: Optional[str] = None,
    verbose: bool = False
) -> Optional[str]:
    """Apply a vertical datum transformation directly to an existing raster file.

    Args:
        input_raster: Path to the input DEM.
        datum_in: Source datum of the DEM.
        datum_out: Target datum for the output DEM.
        output_raster: Path to save the transformed DEM. If None, auto-generates a name.
        decay_pixels: Set the pixel decay in case extrapolation is required.
        cache_dir: Path to store downloaded grids.
        verbose: Enable debug logging.

    Returns:
        str: The path to the transformed output raster, or None if failed.
    """

    import rasterio

    if not os.path.exists(input_raster):
        logger.error(f"Input raster not found: {input_raster}")
        return None

    with rasterio.open(input_raster) as src:
        bounds = src.bounds
        region_obj = (
            Region(bounds.left, bounds.right, bounds.bottom, bounds.top)
        )
        nx, ny = src.width, src.height

    epsg_in, geoid_in = _parse_datum(datum_in)
    epsg_out, geoid_out = _parse_datum(datum_out)

    if not epsg_in or not epsg_out:
        logger.error(f"Invalid datum specified: {datum_in} -> {datum_out}")
        return None

    if not output_raster:
        base, ext = os.path.splitext(input_raster)
        output_raster = f"{base}_trans_{datum_out.replace(':', '_')}{ext}"

    vt = VerticalTransform(
        region=region_obj,
        nx=nx, ny=ny,
        epsg_in=epsg_in, epsg_out=epsg_out,
        geoid_in=geoid_in, geoid_out=geoid_out,
        decay_pixels=decay_pixels,
        cache_dir=cache_dir,
        verbose=verbose
    )

    shift_array, _ = vt._vertical_transform(vt.epsg_in, vt.epsg_out)

    if shift_array is None:
        logger.error("Failed to generate shift array for the raster bounds.")
        return None

    success = GridEngine.apply_vertical_shift(input_raster, shift_array, output_raster)

    if success:
        return output_raster
    return None
