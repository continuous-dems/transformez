#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.htdp
~~~~~~~~~~~~~

Wrapper for the NGS HTDP (Horizontal Time-Dependent Positioning) software.
Transforms coordinates between reference frames (e.g. NAD83 <-> WGS84).

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import os
import subprocess
import tempfile
import logging
import numpy as np
from typing import Optional, Tuple, List

from . import utils
from .definitions import Datums  # Required for ID lookups

logger = logging.getLogger(__name__)

ae = '.exe' if sys.platform == 'win32' else ''
# Validating HTDP existence
htdp_cmd = 'echo 0 | htdp 2>&1' if sys.platform == 'win32' else "echo 0 | htdp 2>&1 | grep SOFTWARE | awk '{print $3}'"
HAS_HTDP = utils.cmd_check(f'htdp{ae}', htdp_cmd)

class HTDP:
    """Wrapper for the NGS HTDP software."""

    def __init__(self, htdp_bin: str = 'htdp', verbose: bool = True):
        self.htdp_bin = htdp_bin
        self.verbose = verbose
        if not HAS_HTDP:
            logger.error('HTDP is not installed or not in PATH.')

    def run_grid(self, region, nx, ny, epsg_in, epsg_out, epoch_in, epoch_out):
        """
        Main entry point called by transform.py.
        Generates a shift grid between two frames.
        """
        if not HAS_HTDP:
            logger.warning("HTDP missing. Returning zero shift.")
            return np.zeros((ny, nx))

        # Look up HTDP numeric IDs (e.g., NAD83=1, WGS84=10)
        # transform.py passes ints (EPSGs), we need HTDP internal IDs
        def get_id(epsg):
            if epsg in Datums.HTDP:
                return Datums.HTDP[epsg]['htdp_id']
            # Fallback for common codes if not in dictionary
            if epsg == 6319: return 1  # NAD83(2011)
            if epsg == 4979: return 10 # WGS84(G1762)
            raise ValueError(f"EPSG {epsg} not defined in HTDP dictionary.")

        try:
            id_in = get_id(epsg_in)
            id_out = get_id(epsg_out)
        except ValueError as e:
            logger.error(e)
            return np.zeros((ny, nx))

        # Create Temporary Workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            in_fn = os.path.join(tmpdir, 'htdp_in.txt')
            out_fn = os.path.join(tmpdir, 'htdp_out.txt')
            ctl_fn = os.path.join(tmpdir, 'htdp.inp')

            # The output Z will be the shift.
            lons = np.linspace(region.xmin, region.xmax, nx)
            lats = np.linspace(region.ymin, region.ymax, ny)

            # Write input file
            with open(in_fn, 'w') as f:
                for y_idx, lat in enumerate(lats):
                    for x_idx, lon in enumerate(lons):
                        # "Lat Lon Height TextID"
                        # We use PNT_x_y tags to robustly map output back to grid
                        f.write(f'{lat:.9f} {lon:.9f} 0.000 "PNT_{x_idx}_{y_idx}"\n')

            # Write Control File
            self._write_control(
                ctl_fn, out_fn, in_fn,
                id_in, epoch_in,
                id_out, epoch_out
            )

            # Run HTDP
            self.run_cmd(ctl_fn)

            # Parse Output & Build Grid
            if not os.path.exists(out_fn):
                logger.error("HTDP produced no output.")
                return np.zeros((ny, nx))

            grid = self._read_grid(out_fn, (ny, nx))

            return grid

    def _read_grid(self, filename: str, shape: Tuple[int, int]) -> np.ndarray:
        """Parses HTDP output, mapping PNT_x_y tags to grid indices."""

        grid = np.zeros(shape)
        with open(filename, 'r') as f:
            for line in f:
                if 'PNT_' not in line: continue

                try:
                    parts = line.replace('"', ' ').split()

                    # HTDP Output Format: Lat, Lon, Height, Text
                    idx_off = 1 if parts[0] == '*' else 0

                    height = float(parts[2 + idx_off])

                    # Parse Tag PNT_x_y
                    tag_part = next(p for p in parts if 'PNT_' in p)
                    _, x_str, y_str = tag_part.split('_')
                    x, y = int(x_str), int(y_str)

                    if 0 <= y < shape[0] and 0 <= x < shape[1]:
                        grid[y, x] = height

                except Exception:
                    continue

        return grid

    def _write_control(self, control_fn, out_fn, in_fn,
                       id_in, epoch_in, id_out, epoch_out):
        """Writes the batch control file."""
        # 4 = Transform Positions
        # 2 = Input file
        # ID_IN
        # ID_OUT
        # 2 = Epoch Format (Decimal Years)
        # EPOCH_IN
        # 2 = Epoch Format
        # EPOCH_OUT
        # 3 = Height (Ellipsoid Height)
        # IN_FILENAME
        # 0 = No Velocities
        # 0 = Standard Output

        content = (
            f"4\n"
            f"{out_fn}\n"
            f"{id_in}\n"
            f"{id_out}\n"
            f"2\n"
            f"{epoch_in}\n"
            f"2\n"
            f"{epoch_out}\n"
            f"3\n"
            f"{in_fn}\n"
            f"0\n"
            f"0\n"
        )
        with open(control_fn, 'w') as f:
            f.write(content)

    def run_cmd(self, control_fn):
        """Executes the binary."""
        try:
            with open(control_fn, 'r') as stdin:
                subprocess.run(
                    [self.htdp_bin],
                    stdin=stdin,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
        except Exception as e:
            logger.error(f"HTDP Runtime Error: {e}")
