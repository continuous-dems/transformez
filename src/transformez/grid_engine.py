#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.grid_engine
~~~~~~~~~~~~~~~~~~~~~~~

Grid compositing utility.
Uses rasterio.warp.reproject (GDAL) with in-memory pre-cleaning to prevent
floating-point nodata leaks and spline ringing at data boundaries.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from scipy import ndimage

logger = logging.getLogger(__name__)


def plot_grid(grid_array, region, title="Vertical Shift Preview"):
    """Plot the transformation grid using Matplotlib."""

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("Matplotlib is not installed. Cannot generate preview.")
        return

    masked_data = np.ma.masked_where(
        (np.isnan(grid_array)) | (grid_array == -9999) | (grid_array == 0), grid_array
    )

    if masked_data.count() == 0:
        logger.warning("Preview skipped: Grid contains no valid data.")
        return

    plt.figure(figsize=(10, 6))
    plot_region = [region.xmin, region.xmax, region.ymin, region.ymax]

    # im = plt.imshow(masked_data, extent=plot_region, cmap="RdBu_r", origin="upper")
    im = plt.imshow(masked_data, extent=plot_region, cmap="viridis", origin="upper")
    cbar = plt.colorbar(im)
    cbar.set_label("Vertical Shift (meters)")
    plt.title(title)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid(True, linestyle=":", alpha=0.6)

    stats = (
        f"Min: {masked_data.min():.3f} m\n"
        f"Max: {masked_data.max():.3f} m\n"
        f"Mean: {masked_data.mean():.3f} m"
    )
    plt.annotate(
        stats,
        xy=(0.02, 0.02),
        xycoords="axes fraction",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
    )
    logger.info("Displaying preview... Close the plot window to continue.")
    plt.show()


class GridEngine:
    @staticmethod
    def load_and_interpolate(source_files, target_region, nx, ny, decay_pixels=100):
        """Composites grids using GDAL Warper."""

        xmin, xmax, ymin, ymax = (
            target_region.xmin,
            target_region.xmax,
            target_region.ymin,
            target_region.ymax,
        )
        dst_transform = from_bounds(xmin, ymin, xmax, ymax, nx, ny)
        dst_crs = "EPSG:4326"

        mosaic = np.full((ny, nx), np.nan, dtype=np.float32)

        for fn in source_files:
            if not os.path.exists(fn) and not fn.startswith("netcdf:"):
                continue

            try:
                with rasterio.open(fn) as src:
                    src_data = src.read(1).astype(np.float32)
                    src_nodata = src.nodata

                    if src_nodata is not None:
                        src_data[np.isclose(src_data, src_nodata, atol=1e-4)] = np.nan
                    if fn.endswith(".gtx"):
                        src_data[np.isclose(src_data, -88.8888, atol=1e-2)] = np.nan

                    temp_buffer = np.full((ny, nx), np.nan, dtype=np.float32)

                    with rasterio.Env(CENTER_LONG=0):
                        reproject(
                            source=src_data,
                            destination=temp_buffer,
                            src_transform=src.transform,
                            src_crs=src.crs or "EPSG:4326",
                            src_nodata=np.nan,
                            dst_transform=dst_transform,
                            dst_crs=dst_crs,
                            dst_nodata=np.nan,
                            resampling=Resampling.bilinear,
                        )

                    valid_mask = ~np.isnan(temp_buffer)
                    mosaic[valid_mask] = temp_buffer[valid_mask]

            except Exception as e:
                logger.warning(f"Failed to reproject {fn}: {e}")
                continue

        # Fill inland areas (decaying to 0) before we clear the remaining NaNs
        # mosaic = GridEngine.fill_nans(mosaic, decay_pixels=decay_pixels)
        # mosaic[np.isnan(mosaic)] = 0.0

        return mosaic

    @staticmethod
    def smart_blend(in_grid, background_grid, blend_pixels=50):
        """Smoothly blends the grid into a background grid."""

        mask = np.isnan(in_grid)

        if not mask.any():
            return in_grid

        if mask.all():
            return background_grid

        dist = ndimage.distance_transform_edt(mask)
        alpha = np.clip(dist / blend_pixels, 0.0, 1.0)

        nearest_indices = ndimage.distance_transform_edt(
            mask, return_distances=False, return_indices=True
        )
        extended_vdatum = in_grid.copy()
        extended_vdatum[mask] = in_grid[tuple(nearest_indices)][mask]

        blended_data = (extended_vdatum * (1.0 - alpha)) + (background_grid * alpha)

        return blended_data

    @staticmethod
    def coastal_aware_composite(
        vdatum_grid,
        global_grid,
        decay_pixels=100,
        buffer_pixels=10,
        max_discontinuity=0.5,
    ):
        """Intelligently handles inland decay vs. offshore blending, while
        filtering out low-resolution global artifacts.
        """

        final_grid = vdatum_grid.copy()
        vdatum_mask = np.isnan(vdatum_grid)
        if not vdatum_mask.all():
            nearest_idx = ndimage.distance_transform_edt(
                vdatum_mask, return_distances=False, return_indices=True
            )
            nearest_vdatum_vals = vdatum_grid[tuple(nearest_idx)]

            fes_anomaly_mask = (
                np.abs(global_grid - nearest_vdatum_vals) > max_discontinuity
            )

            global_grid[fes_anomaly_mask] = np.nan

        is_vdatum = ~np.isnan(vdatum_grid)
        is_ocean = ~np.isnan(global_grid)

        is_inland = ~is_vdatum & ~is_ocean
        is_offshore = ~is_vdatum & is_ocean

        if is_offshore.any():
            blended_ocean = GridEngine.smart_blend(
                vdatum_grid, global_grid, blend_pixels=50
            )
            final_grid[is_offshore] = blended_ocean[is_offshore]

        if is_inland.any():
            decayed_inland = GridEngine.fill_nans(
                vdatum_grid, decay_pixels=decay_pixels, buffer_pixels=buffer_pixels
            )
            final_grid[is_inland] = decayed_inland[is_inland]

        return final_grid

    @staticmethod
    def fill_nans(data, decay_pixels=100, buffer_pixels=50):
        """Extrapolates nearest valid value for 'buffer_pixels',
        then decays to zero over 'decay_pixels'.
        """

        mask = np.isnan(data)
        if not mask.any() or mask.all():
            return data

        dist, indices = ndimage.distance_transform_edt(
            mask, return_distances=True, return_indices=True
        )
        coast_values = data[tuple(indices)]

        # Subtract the buffer from the distance. Anything <= 0 is in the buffer zone.
        effective_dist = np.clip(dist - buffer_pixels, 0, None)
        decay_factor = np.clip((decay_pixels - effective_dist) / decay_pixels, 0, 1)

        out_data = data.copy()
        out_data[mask] = coast_values[mask] * decay_factor[mask]

        return out_data

    @staticmethod
    def apply_vertical_shift(
        src_dem, shift_array, dst_dem, z_unit_in="m", z_unit_out="m"
    ):
        """Apply a vertical shift array to a source DEM."""

        from .definitions import Datums

        factor_in = Datums.get_unit_factor(z_unit_in)
        factor_out = Datums.get_unit_factor(z_unit_out)

        try:
            with rasterio.open(src_dem) as src:
                profile = src.profile.copy()
                data = src.read(1)

                if data.shape != shift_array.shape:
                    raise ValueError(
                        f"Dimension mismatch: DEM {data.shape} vs Shift {shift_array.shape}"
                    )

                nodata = src.nodata if src.nodata is not None else -9999
                profile.update(nodata=nodata)

                valid_mask = (data != nodata) & (~np.isnan(shift_array))

                # Scale input to meters
                data_meters = data[valid_mask] * factor_in

                # Add the meter-based datum shift
                data_shifted_meters = data_meters + shift_array[valid_mask]

                # Scale to target output units
                data[valid_mask] = data_shifted_meters / factor_out
                data[~valid_mask] = nodata

                # valid_mask = (data != nodata) & (~np.isnan(shift_array))
                # data[valid_mask] += shift_array[valid_mask]
                # data[~valid_mask] = nodata

                with rasterio.open(dst_dem, "w", **profile) as dst:
                    dst.write(data, 1)
            logger.info(f"Successfully wrote transformed DEM to: {dst_dem}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply shift to DEM: {e}")
            return False


class GridWriter:
    @staticmethod
    def write(filename, data, region):
        """Write a vertical shift grid using Rasterio."""

        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

        if not filename.endswith(".tif"):
            filename = os.path.splitext(filename)[0] + ".tif"

        rows, cols = data.shape
        xmin, xmax, ymin, ymax = region.xmin, region.xmax, region.ymin, region.ymax

        res_x = (xmax - xmin) / cols
        res_y = (ymax - ymin) / rows
        transform = rasterio.transform.from_origin(xmin, ymax, res_x, res_y)

        with rasterio.open(
            filename,
            "w",
            driver="GTiff",
            height=rows,
            width=cols,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            compress="deflate",
            tiled=True,
        ) as dst:
            dst.write(data.astype("float32"), 1)
        return filename
