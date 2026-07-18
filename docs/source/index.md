# Transformez Documentation

**Global vertical datum transformations, simplified**

*Transformez Les Données*

**Transformez** is a standalone Python engine for converting geospatial data between vertical datums (e.g., `MLLW` ↔ `NAVD88` ↔ `Ellipsoid`).

Originally developed as the core transformation engine for the [CUDEM](https://github.com/continuous-dems/cudem) project, Transformez has evolved into a standalone datum transformation suite.

## Quickstart

![Shift Grid Example](_static/mllw2nvd.png)
*(Above: A generated vertical shift grid transforming MLLW to NAVD88)*

```transformez grid -R loc:"new orleans" -E 3s -I mllw -O 5703```

**Installation**

```bash
pip install transformez
```

## Command Line Interface:

**Generate a vertical shift grid for anywhere on Earth.**

```bash
transformez grid -R -166/-164/63/64 -E 1s -I mllw -O 4979
```

**Transform a raster directly.** Transformez reads the bounds/resolution from the file.

```bash
transformez raster my_dem.tif -I mllw -O 5703
```

## Python API

Transformez provides a high-level [API](api/index.md) for embedding transformations directly into your Python scripts, Jupyter Notebooks, or automated pipelines.

```python
import transformez

# Generate a Shift Grid
# Returns a 2D numpy array. Optionally saves to a file.
# Requesting "mllw" in India triggers the Global Fallback (FES2014) automatically.
shift_array = transformez.generate_grid(
    region=[80, 85, 10, 15],  # [West, East, South, North]
    increment="3s",           # Grid resolution
    datum_in="mllw",
    datum_out="4979",         # WGS84 Ellipsoid
    out_fn="india_shift.tif"  # Optional: Save to disk
)

# Transform an Existing Raster
# Applies the datum shift directly to a DEM and saves the result.
out_file = transformez.transform_raster(
    input_raster="my_dem_mllw.tif",
    datum_in="mllw",
    datum_out="5703:g2012b",  # NAVD88 using specific GEOID12B
    decay_pixels=0,           # Set to 0 for infinite inland extrapolation (Modeling)
    output_raster="my_dem_navd88.tif"
)
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: User Guide:

user_guide/index
api/index
```

Indices and tables
==================

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
