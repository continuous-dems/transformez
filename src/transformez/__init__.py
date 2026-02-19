#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
transformez
~~~~~~~~~~~~~

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

__version__ = "0.2.0"
__author__ = "Matthew Love"
__credits__ = "CIRES"

import os
import glob
# from .hooks import TransformezHook
# from fetchez.hooks.registry import HookRegistry
from fetchez.registry import FetchezRegistry

from .modules import TransformezMod

def _find_proj_lib():
    """Locate the best available PROJ_LIB path."""

    try:
        import rasterio
        r_path = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")
        if os.path.exists(os.path.join(r_path, "proj.db")):
            return r_path

        parent = os.path.dirname(os.path.dirname(rasterio.__file__))
        libs = glob.glob(os.path.join(parent, "rasterio.libs*"))
        if libs:
            for root, _, files in os.walk(libs[0]):
                if "proj.db" in files:
                    return root
    except ImportError:
        pass

    try:
        import pyproj
        p_path = pyproj.datadir.get_data_dir()
        if os.path.exists(os.path.join(p_path, "proj.db")):
            return p_path
    except ImportError:
        pass

    return None

target_proj_lib = _find_proj_lib()

if "PROJ_LIB" in os.environ:
    del os.environ["PROJ_LIB"]

if target_proj_lib:
    os.environ["PROJ_LIB"] = target_proj_lib

def setup_fetchez(registry_cls):
    """Called by fetchez when loading plugins.

    Registers modules, hooks, and presets.
    """

    registry_cls.register_module(
        'transformez',
        TransformezMod,
        metadata={
            'desc': 'Generate vertical datum shift grids on-demand.',
            "tags": ["vdatum", "transformation", "shift-grid"],
            "category": "Tools"
        }
    )

    # HookRegistry.register_hook(TransformezHook)
    # from fetchez.presets import register_global_preset
    # register_global_preset(
    #     name="make-shift-grid",
    #     help_text="Download datum grids and composite them into a single shift grid.",
    #     hooks=[
    #         {"name": "transformez", "args": {}}
    #     ]
    # )
setup_fetchez(FetchezRegistry)
