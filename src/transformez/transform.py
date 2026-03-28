#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez.transform
~~~~~~~~~~~~~

Main transformation logic.
Implements a Dynamic Hub-and-Spoke model.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
import gzip
import shutil
import numpy as np
import fetchez

from .definitions import Datums
from .grid_engine import GridEngine

logger = logging.getLogger(__name__)

# Default Hubs
WGS84_EPSG = 4979
NAD83_EPSG = 6319


class VerticalTransform:
    """Generate a vertical transformation grid using Transformez."""

    def __init__(
        self,
        region,
        nx,
        ny,
        epsg_in,
        epsg_out,
        geoid_in=None,
        geoid_out=None,
        epoch_in=2010.0,
        epoch_out=2010.0,
        decay_pixels=100,
        cache_dir=None,
        verbose=True,
    ):

        self.region = region
        self.nx = nx
        self.ny = ny
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), "transformez_cache")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.verbose = verbose

        self.epsg_in = Datums.get_vdatum_by_name(str(epsg_in))
        self.epsg_out = Datums.get_vdatum_by_name(str(epsg_out))

        self.geoid_in = geoid_in or Datums.get_default_geoid(self.epsg_in)
        self.geoid_out = geoid_out or Datums.get_default_geoid(self.epsg_out)

        self.epoch_in = float(epoch_in) if epoch_in else 2010.0
        self.epoch_out = float(epoch_out) if epoch_out else 2010.0

        self.ref_in = Datums.get_frame_type(self.epsg_in)
        self.ref_out = Datums.get_frame_type(self.epsg_out)

        self.decay_pixels = decay_pixels

        # --- HUB SELECTION ---
        # Determine the Native Ellipsoid of Input and Output
        native_in = self._get_native_ellipsoid(self.epsg_in, self.ref_in)
        native_out = self._get_native_ellipsoid(self.epsg_out, self.ref_out)

        # If both are NAD83, stay in NAD83. Otherwise, go to WGS84.
        if native_in == NAD83_EPSG and native_out == NAD83_EPSG:
            self.hub_epsg = NAD83_EPSG
            if self.verbose:
                logger.info(f"Using Native Hub: NAD83 (EPSG:{self.hub_epsg})")
        else:
            self.hub_epsg = WGS84_EPSG
            if self.verbose:
                logger.info(f"Using Global Hub: WGS84 (EPSG:{self.hub_epsg})")

    def _get_native_ellipsoid(self, epsg, ref_type):
        """Helper to identify the native frame of a datum."""

        if ref_type in ["surface", "global_tidal"]:
            # NOAA VDatum = NAD83, Global = WGS84
            region = Datums.SURFACES[epsg].get("region")
            return NAD83_EPSG if region == "usa" else WGS84_EPSG
        elif ref_type == "cdn":
            # Look up in definitions, default to NAD83 for US geoids
            return Datums.CDN.get(epsg, {}).get("ellipsoid", NAD83_EPSG)
        elif ref_type == "htdp":
            # If it's a Frame, it is its own native ellipsoid
            return epsg
        return WGS84_EPSG  # Default

    def fetch_grid(self, module_name, **kwargs):
        """Generic fetcher wrapper using the new fetchez API."""

        files = fetchez.get(
            module=module_name,
            region=self.region.to_list(),
            outdir=self.cache_dir,
            threads=2,
            **kwargs,
        )

        valid = []

        for fn in files:
            if not os.path.exists(fn):
                continue

            if fn.endswith(".zip"):
                datatype = kwargs.get("datatype")
                fns_to_extract = [datatype] if datatype else None
                extracted = fetchez.utils.p_f_unzip(
                    fn, fns=fns_to_extract, outdir=self.cache_dir
                )
                valid.extend(
                    [
                        f
                        for f in extracted
                        if f.endswith((".gtx", ".tif", ".grd", ".nc"))
                    ]
                )

            elif fn.endswith(".gz"):
                try:
                    out_fn = os.path.splitext(fn)[0]
                    if not os.path.exists(out_fn):
                        logger.info(f"Decompressing {fn}...")
                        with gzip.open(fn, "rb") as f_in:
                            with open(out_fn, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)
                    valid.append(out_fn)
                except Exception as e:
                    logger.error(f"Failed to decompress {fn}: {e}")

            elif fn.endswith((".gtx", ".tif", ".grd", ".nc", ".mss")):
                valid.append(fn)

        return valid

    def fetch_grid_(self, module_name, **kwargs):
        """Generic fetcher wrapper."""

        Mod = fetchez.modules.registry.FetchezRegistry.load_module(module_name)
        if not Mod:
            return []

        fetcher = Mod(src_region=self.region, **kwargs)
        fetcher.run()
        if fetcher.results:
            fetchez.core.run_fetchez([fetcher], threads=2)
        valid = []
        for r in fetcher.results:
            fn = r["dst_fn"]
            if not os.path.exists(fn):
                continue

            if fn.endswith(".zip"):
                extracted = fetchez.utils.p_f_unzip(
                    fn, fns=[r["data_type"]], outdir=self.cache_dir
                )
                valid.extend(
                    [
                        f
                        for f in extracted
                        if f.endswith((".gtx", ".tif", ".grd", ".nc"))
                    ]
                )
            elif fn.endswith(".gz"):
                try:
                    out_fn = os.path.splitext(fn)[0]
                    if not os.path.exists(out_fn):
                        logger.info(f"Decompressing {fn}...")
                        with gzip.open(fn, "rb") as f_in:
                            with open(out_fn, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)

                    valid.append(out_fn)
                except Exception as e:
                    logger.error(f"Failed to decompress {fn}: {e}")
            elif fn.endswith((".gtx", ".tif", ".grd", ".nc", ".mss")):
                valid.append(fn)
        return valid

    def _get_grid(self, provider, name):
        if not name:
            return np.zeros((self.ny, self.nx))

        if not provider:
            provider = "proj"

        if "geoid=" in name:
            name = name.split("=")[1]

        files = self.fetch_grid(provider, datatype=name, query=name)
        if not files:
            return np.zeros((self.ny, self.nx))

        if provider == "seanoe" or provider == "fes":
            var_name = "lat_elevation" if "lat" in name.lower() else "msl_elevation"
            nc_path = f"netcdf:{files[0]}:{var_name}"
            return GridEngine.load_and_interpolate(
                [nc_path], self.region, self.nx, self.ny, decay_pixels=self.decay_pixels
            )

        return GridEngine.load_and_interpolate(
            files, self.region, self.nx, self.ny, decay_pixels=self.decay_pixels
        )

    def _get_htdp_shift(self, epsg_from, epsg_to, epoch_from, epoch_to):
        """Calculate Frame Shift via HTDP."""

        if epsg_from == epsg_to and epoch_from == epoch_to:
            return np.zeros((self.ny, self.nx))

        from . import htdp

        try:
            logger.info(f"    [HTDP] Frame Shift: EPSG:{epsg_from} -> EPSG:{epsg_to}")
            tool = htdp.HTDP(verbose=False)
            grid = tool.run_grid(
                self.region, self.nx, self.ny, epsg_from, epsg_to, epoch_from, epoch_to
            )
            if np.any(grid):
                logger.info(f"    [HTDP] Component Shift (Mean: {np.mean(grid):.3f}m)")
            return grid

        except Exception as e:
            logger.error(f"    [HTDP] Failed: {e}")
            return np.zeros((self.ny, self.nx))

    def _fetch_geoid_with_fallback(self, target_geoid):
        """Fetches a geoid grid. If the primary geoid lacks coverage (e.g., GEOID18 in AK),
        it automatically falls back to older, compatible models.
        """

        # Ordered list of preferred US geoids (Newest to Oldest)
        us_geoids = ["g2018", "g2012b", "geoid09"]

        if target_geoid in us_geoids:
            start_idx = us_geoids.index(target_geoid)
            geoids_to_try = us_geoids[start_idx:]
        else:
            geoids_to_try = [target_geoid]

        for g in geoids_to_try:
            geoid_def = Datums.GEOIDS.get(g, {})
            provider = geoid_def.get("provider", "proj")
            grid = self._get_grid(provider, g)

            if np.any(grid):
                if g != target_geoid and self.verbose:
                    logger.info(
                        f"    [Geoid Fallback] '{target_geoid}' lacks coverage here. Falling back to '{g}'."
                    )
                return grid, g

        return np.zeros((self.ny, self.nx)), target_geoid

    # =========================================================================
    # Chains
    # =========================================================================
    def _get_vdatum_chain(self, datum_name, geoid_name):
        """Builds shift: Tidal -> [NAD83 Native]."""
        hydro_shift = np.zeros((self.ny, self.nx))
        desc = []

        # Tidal -> LMSL
        if datum_name not in ["msl", "5714", "lmsl"]:
            grid = self._get_grid("vdatum", datum_name)
            if np.isnan(grid).all() or (grid == 0).all():
                return None, f"Missing Tidal Grid: {datum_name}"
            hydro_shift += grid
            desc.append(f"({datum_name}->LMSL)")

        # LMSL -> Ortho (TSS)
        tss = self._get_grid("vdatum", "tss")
        if np.isnan(tss).all() or (tss == 0).all():
            return None, "Outside VDatum coverage (Missing TSS)"

        hydro_shift += tss
        desc.append("TSS(LMSL->NAVD88)")

        # Ortho -> NAD83 (Geoid)
        # We fetch the geoid, but DO NOT add it to the shift yet!
        actual_geoid = geoid_name if geoid_name else "g2018"
        geoid_grid, used_geoid = self._fetch_geoid_with_fallback(actual_geoid)
        desc.append(f"Geoid({used_geoid}->NAD83)")

        # =======================================================
        # Coastal Blend
        # =======================================================
        total_shift = np.zeros((self.ny, self.nx))

        if np.isnan(hydro_shift).any():
            proxy_name = Datums.get_global_proxy(datum_name)
            if proxy_name:
                logger.info(
                    f"Partial VDatum coverage detected. Fetching {proxy_name.upper()} (FES) for offshore blending..."
                )
                global_shift, d_global = self._get_global_chain(
                    proxy_name, model="fes2014"
                )

                if global_shift is not None and np.any(global_shift):
                    # We have valid FES data. We must align it to NAD83.
                    htdp_wgs_to_nad = self._get_htdp_shift(
                        WGS84_EPSG, NAD83_EPSG, self.epoch_in, 2010.0
                    )
                    fes_full = global_shift + htdp_wgs_to_nad

                    hydro_shift = GridEngine.coastal_aware_composite(
                        vdatum_grid=hydro_shift,
                        global_grid=fes_full,
                        decay_pixels=self.decay_pixels,
                        buffer_pixels=10,
                        max_discontinuity=0.5,
                    )
                    desc.append(f"Blended w/ Global({proxy_name.upper()})")
                else:
                    hydro_shift = GridEngine.fill_nans(
                        hydro_shift, decay_pixels=self.decay_pixels, buffer_pixels=10
                    )
                    desc.append("Inland Hydro Decay")
            else:
                hydro_shift = GridEngine.fill_nans(
                    hydro_shift, decay_pixels=self.decay_pixels, buffer_pixels=10
                )
                desc.append("Inland Hydro Decay")

        total_shift = hydro_shift + geoid_grid
        total_shift[np.isnan(total_shift)] = 0.0

        return total_shift, " + ".join(desc)

    def _get_global_chain(self, datum_name, model="fes2014"):
        """Builds shift: Global Tidal -> WGS84 Native."""

        total_shift = np.zeros((self.ny, self.nx))
        desc = []

        model_def = Datums.MODELS.get(model)
        if not model_def:
            return total_shift, "Error"

        provider = model_def["provider"]

        # Tidal -> MSS
        if datum_name in ["lat", "hat"]:
            grid_name = model_def["grids"].get(datum_name)
            if grid_name:
                grid = self._get_grid(provider, grid_name)
                # Sign Correction
                if datum_name == "lat" and np.nanmean(grid) > 0:
                    grid *= -1.0
                elif datum_name == "hat" and np.nanmean(grid) < 0:
                    grid *= -1.0

                total_shift += grid
                desc.append(f"{datum_name.upper()}->MSS")

        # MSS -> WGS84
        mss_name = model_def["grids"].get("mss")
        if mss_name:
            mss_grid = self._get_grid(provider, mss_name)
            if provider == "seanoe" or "fes" in model.lower():
                mss_grid -= 0.70
                desc.append("MSS->WGS84(TP_Corr)")
            else:
                desc.append("MSS->Ellipsoid")

            total_shift += mss_grid

        if not desc:
            return total_shift, "Global Chain (Empty)"

        return total_shift, " + ".join(desc)

    # =========================================================================
    # Steps
    # =========================================================================
    def _step_to_hub(self, epsg, ref_type, geoid=None, epoch=None):
        shift = np.zeros((self.ny, self.nx))
        if epsg == self.hub_epsg:
            return shift, "Already at Hub"

        native_epsg = self._get_native_ellipsoid(epsg, ref_type)
        chain_shift = None
        chain_desc = ""

        if ref_type in ["surface", "global_tidal"]:
            datum_name = Datums.SURFACES[epsg]["name"]
            region_tag = Datums.SURFACES[epsg].get("region")

            if region_tag == "usa":
                s, d = self._get_vdatum_chain(datum_name, geoid)
                if s is None:
                    native_epsg = WGS84_EPSG
                    proxy_name = Datums.get_global_proxy(datum_name)
                    if proxy_name:
                        s, d = self._get_global_chain(proxy_name, model="fes2014")
                        # d = f"Global({proxy_name}) [Proxy] -> WGS84"
                chain_shift, chain_desc = s, d

            elif region_tag == "global":
                chain_shift, chain_desc = self._get_global_chain(datum_name)

        elif ref_type == "cdn":
            target_geoid = geoid if geoid else "g2018"
            chain_shift, used_geoid = self._fetch_geoid_with_fallback(target_geoid)
            chain_desc = f"Ortho(via {used_geoid}) -> Frame({native_epsg})"

        elif ref_type == "htdp":
            chain_shift = np.zeros((self.ny, self.nx))
            chain_desc = f"Frame({epsg})"

        if chain_shift is not None:
            if native_epsg != self.hub_epsg:
                htdp_shift = self._get_htdp_shift(
                    native_epsg, self.hub_epsg, epoch, self.epoch_out
                )
                chain_shift += htdp_shift
                chain_desc += f" + Frame({native_epsg}->{self.hub_epsg})"
            return chain_shift, chain_desc

        return shift, ""

    def _step_from_hub(self, epsg, ref_type, geoid=None, epoch=None):
        shift = np.zeros((self.ny, self.nx))
        if epsg == self.hub_epsg:
            return shift, "Remain at Hub"

        native_epsg = self._get_native_ellipsoid(epsg, ref_type)
        total_out = np.zeros((self.ny, self.nx))
        desc_parts = []

        htdp_shift = np.zeros((self.ny, self.nx))

        if self.hub_epsg != native_epsg:
            htdp_shift = self._get_htdp_shift(
                self.hub_epsg, native_epsg, self.epoch_in, epoch
            )
            total_out += htdp_shift
            desc_parts.append(f"Hub({self.hub_epsg}->{native_epsg})")

        if ref_type in ["surface", "global_tidal"]:
            datum_name = Datums.SURFACES[epsg]["name"]
            region_tag = Datums.SURFACES[epsg].get("region")
            chain_geoid = geoid if geoid else "g2018"

            if region_tag == "usa":
                s, d = self._get_vdatum_chain(datum_name, chain_geoid)
                if s is None:
                    proxy_name = Datums.get_global_proxy(datum_name)
                    if proxy_name:
                        # Revert the erroneous HTDP shift to NAD83 (since global is WGS84)
                        total_out -= htdp_shift
                        if desc_parts:
                            desc_parts.pop()

                        s, d = self._get_global_chain(proxy_name, model="fes2014")
                        if s is not None:
                            total_out -= s
                            desc_parts.append(f"GlobalProxy({proxy_name})")
                        else:
                            return np.zeros(
                                (self.ny, self.nx)
                            ), "FAILED Output Global Chain"
                    else:
                        return np.zeros((self.ny, self.nx)), "FAILED Output Chain"
                else:
                    total_out -= s
                    desc_parts.append(f"Native -> VDatum({datum_name})")

            elif region_tag == "global":
                s, d = self._get_global_chain(datum_name)
                if s is not None:
                    total_out -= s
                    desc_parts.append(f"Native -> Global({datum_name})")

        elif ref_type == "cdn":
            target_geoid = geoid if geoid else "g2018"
            geoid_grid, used_geoid = self._fetch_geoid_with_fallback(target_geoid)

            if not np.any(geoid_grid):
                logger.warning(
                    f"Geoid {target_geoid} (and fallbacks) not found/covered."
                )

            total_out -= geoid_grid
            desc_parts.append(f"Native -> Ortho(via {used_geoid})")

        return total_out, " + ".join(desc_parts)

    def _vertical_transform(self, epsg_in, epsg_out):
        logger.info("-" * 60)
        logger.info(f"Transformation Plan: {self.epsg_in} -> {self.epsg_out}")
        logger.info(f"Hub Frame: EPSG:{self.hub_epsg}")

        total_shift = np.zeros((self.ny, self.nx))
        total_unc = np.zeros((self.ny, self.nx))

        if self.epsg_in == self.epsg_out:
            logger.info("  1. Identity Transform (Zero Shift)")
            return total_shift, total_unc

        # Input -> Hub
        grid_1, desc_1 = self._step_to_hub(
            self.epsg_in, self.ref_in, self.geoid_in, self.epoch_in
        )
        if np.any(grid_1):
            logger.info(f"  1. {desc_1}")
            total_shift += grid_1
        else:
            logger.info(f"  1. {desc_1} (No Shift/Zero)")

        # Hub -> Output
        grid_2, desc_2 = self._step_from_hub(
            self.epsg_out, self.ref_out, self.geoid_out, self.epoch_out
        )
        if np.any(grid_2):
            logger.info(f"  2. {desc_2}")
            total_shift += grid_2
        else:
            logger.info(f"  2. {desc_2} (No Shift/Zero)")

        if np.any(total_shift) and not np.isnan(total_shift).all():
            mean_shift = np.nanmean(total_shift)
            min_shift = np.nanmin(total_shift)
            max_shift = np.nanmax(total_shift)
            logger.info(
                f"  => Total Shift Applied (Mean: {mean_shift:.3f}m | Min: {min_shift:.3f}m | Max: {max_shift:.3f}m)"
            )
        else:
            logger.info("  => Total Shift Applied (Zero / Identity)")

        logger.info("-" * 60)
        return total_shift, total_unc
