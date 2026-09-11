# 🛠️ Usage

Transformez can be used directly from the command line or Python API, or through integrations such as Fetchez and QGIS. All interfaces (CLI, Python API, and integrations such as Fetchez and QGIS) accept the same [references](references.md) and behave identically.

> **🧮 Sign conventions:** vertical datum shifts are not always intuitive (shifting to a *higher* surface does not simply mean positive values). Transformez handles all sign conventions internally. The one thing to remember: **always ADD the shift grid** to your elevation data. See the [sign conventions](methodology.md#the-datum-shift-sign-conventions) section of the methodology guide for the physical intuition.

## Command Line Interface

**Generate a vertical shift grid anywhere on Earth.**

```bash
# Transform MLLW to WGS84 ellipsoidal height in Norton Sound, AK
transformez build -R -166/-164/63/64 -E 1s -I vdatum:mllw -O epsg:4979
```

**Transform a raster directly.** Transformez reads the bounds/resolution from the file.

```bash
transformez shift my_dem.tif \
    -I epsg:5703 -O vdatum:mhw \
    --decay-distance 5000 \
    --buffer-distance 250
```

> See [Command Line Interface](cli_usage.md) for the full command reference.


## Python API:

Transformez provides a high-level API for embedding transformations directly into your Python scripts, Jupyter Notebooks, or automated pipelines.

```python
import transformez

# ---------------------------------------------------------
# Generate a Shift Grid
# ---------------------------------------------------------
# Returns a 2D numpy array. Optionally saves to a file.
# Outside VDatum coverage, vdatum:mllw is realized through the configured global tidal fallback.

shift_array = transformez.generate_grid(
    region=[80, 85, 10, 15],  # [West, East, South, North]
    increment="3s",           # Grid resolution
    datum_in="vdatum:mllw",   # VDatums mllw realization
    datum_out="epsg:4979",    # WGS84 Ellipsoid
    out_fn="india_shift.tif"  # Optional: Save to disk
)

# ---------------------------------------------------------
# Transform an Existing Raster
# ---------------------------------------------------------
# Applies the datum shift directly to a DEM and saves the result.

out_file = transformez.transform_raster(
    input_raster="my_dem_lat.tif",
    datum_in="global:lat",
    datum_out="epsg:5703",
    extrapolate_inland=False,
    output_raster="my_dem_navd88.tif"
)
```


(which-interface-do-i-want)=
## Which interface do I want?

For most users, `transformez.generate_grid(...)` is all you need. This will return a 2D NumPy array of shift values, optionally saved to disk as a GIS-compatible raster.

When you need a fully georeferenced, inspectable transformation product, use `build_shift_grid(...)` to obtain a `ShiftGrid` object. It carries the array, region, CRS, affine transform, source and target references, epochs, provenance, generation key, uncertainty, and cache identity, and can write or reproject itself.

```python
grid = build_shift_grid(...)

grid.array
grid.crs
grid.transform
grid.source_reference
grid.target_reference
grid.provenance

grid.write(...)        # Write to disk
grid.reproject(...)    # Return a reprojected ShiftGrid
```

> Use `generate_grid()` when you only need shift values.
> Use `build_shift_grid()` when you need a georeferenced, inspectable transformation product.

For full DEM-to-DEM transformation (horizontal reprojection and vertical transformation), `build_components()` parses complete compound references and returns a horizontal transformer plus a vertical `ShiftGrid`:

```python
components = transformez.build_components(
    "EPSG:4326+5703",
    "EPSG:32610+4979",
    region=region,
)

components.horizontal
components.vertical
```

Full signatures for these functions are in the [Developer API](../api/api.md).

## Inland Decay vs. Unrestricted Extrapolation

By default, Transformez decays tidal transformations to zero inland using a physical distance from the coastline (defaults: a 250 m full-strength buffer followed by a 5.0 km decay). This suits typical coastal DEM work, where tidal datums physically do not exist on dry land.

Some hydrodynamic, tsunami, storm-surge, and inundation workflows instead require the coastal transformation to continue across all terrain that may become wetted during the simulation. For those cases, disable inland decay:

```bash
transformez shift my_coastal_dem.tif \
    -I epsg:5703 -O vdatum:mhw \
    --extrapolate-inland
```

> The sign conventions of the applied shift and the physical intuition behind coastal blending and inland decay are covered in depth in [Methodology](methodology.md); the models being fetched are listed in [Models and Providers](providers.md).


## Integrations

Transformez can also be used through integrations with other geospatial tools:

* **Fetchez:** Transformez can operate as a Fetchez plugin, allowing datum transformations and shift-grid generation to be incorporated directly into data-fetching workflows.
* **QGIS:** The Transformez QGIS plugin generates vertical shift grids for the current map extent from a graphical interface. It installs and manages Transformez in an isolated runtime, wrapping the public Python API.
