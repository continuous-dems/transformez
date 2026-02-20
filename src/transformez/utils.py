#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.utils
~~~~~~~~~~~~~

This holds various utility functions.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import subprocess
import logging
import numpy as np
import rasterio

logger = logging.getLogger(__name__)
cmd_exists = lambda x: any(os.access(os.path.join(path, x), os.X_OK)
                           for path in os.environ['PATH'].split(os.pathsep))


def run_cmd(args):
    """Standalone replacement for utils.run_cmd using subprocess."""

    logger.info(f"Running: {' '.join(args) if isinstance(args, list) else args}")

    result = subprocess.run(
        args,
        shell=False if isinstance(args, list) else True,
        capture_output=True,
        text=True
    )
    return result.stdout, result.returncode


def cmd_check(cmd_str, cmd_vers_str):
    """check system for availability of 'cmd_str'"""

    if cmd_exists(cmd_str):
        cmd_vers, status = run_cmd(f"{cmd_vers_str}")
        return cmd_vers.rstrip()
    return b"0"


class RasterQuery:
    """Raster query for point clouds.
    Pre-loads raster data and inverse transform to rapidly query (X, Y) arrays.
    """

    def __init__(self, filename, default_nodata=0.0):
        if not filename or not os.path.exists(filename):
            raise FileNotFoundError(f"Raster not found: {filename}")

        self.default_nodata = default_nodata

        with rasterio.open(filename) as src:
            self.data = src.read(1)
            self.transform = src.transform
            self.inv_transform = ~src.transform
            self.bounds = src.bounds
            self.width = src.width
            self.height = src.height

            if src.nodata is not None:
                self.data[self.data == src.nodata] = self.default_nodata
            self.data = np.nan_to_num(self.data, nan=self.default_nodata)

    def query(self, x, y):
        """query the raster at given X, Y numpy arrays using pure vectorized affine math."""

        q_x = np.asarray(x).copy()
        q_y = np.asarray(y)

        if self.bounds.left < 0 and np.any(q_x > 180):
            q_x = np.where(q_x > 180, q_x - 360, q_x)
        elif self.bounds.left >= 0 and np.any(q_x < 0):
            q_x = np.where(q_x < 0, q_x + 360, q_x)

        cols_f, rows_f = self.inv_transform * (q_x, q_y)

        cols = np.floor(cols_f).astype(int)
        rows = np.floor(rows_f).astype(int)

        valid = (
            (rows >= 0) & (rows < self.height) &
            (cols >= 0) & (cols < self.width)
        )

        results = np.full_like(q_x, self.default_nodata, dtype=self.data.dtype)
        if np.any(valid):
            results[valid] = self.data[rows[valid], cols[valid]]

        return results
