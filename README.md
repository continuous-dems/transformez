<p align="center">
	<a href="https://github.com/continuous-dems">
		<img src="https://raw.githubusercontent.com/continuous-dems/transformez/refs/heads/main/docs/source/_static/transformez-logo.svg" height="80" alt="Continuous DEMs Logo">
	</a>
</p>
<h1 align="center">Transformez</h1>
<p align="center"><strong>Global vertical datum transformations, simplified.</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12+-yellow.svg" alt="Python"></a>
  <a href="https://badge.fury.io/py/transformez"><img src="https://badge.fury.io/py/transformez.svg" alt="PyPI version"></a>
  <a href="https://anaconda.org/conda-forge/transformez"><img src="https://img.shields.io/conda/vn/conda-forge/transformez.svg" alt="Conda Version"></a>
  <a href="https://cudem.zulip.org"><img src="https://img.shields.io/badge/zulip-join_chat-brightgreen.svg" alt="Project Chat"></a>
  <a href="https://doi.org/10.5281/zenodo.22131424"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.22131423.svg" alt="DOI"></a>
</p>

**Transformez** builds and applies vertical transformations across geodetic, tidal, and model-based height references, from local datums to global surfaces.

Rather than applying a fixed, constant offset from a single tide gauge, Transformez resolves your input and output references, computes the optimal geodetic pathway on the fly, and generates **spatially varying shift grids** — where regional models like NOAA VDatum end, the transformation continues seamlessly across open ocean and inland via global proxies, coastal blending, and meter-based inland decay.

Transformez is part of the [Continuous DEMs Project](https://continuous-dems.readthedocs.io/), an ecosystem of tools for modern, continuous digital elevation model generation. Originally incubated within CUDEM, the engine has evolved into a standalone datum transformation suite.

---

## 📦 Installation

Install the Transformez Python package:

```bash
pip install transformez

# Install the external geodetic engines through the CLI (HTDP is only needed for dynamic-frame and epoch transformations):
transformez htdp install
transformez vdatum install   # optional, for direct VDatum comparison/validation
```

## 🚀 Quickstart

Generate a vertical shift grid anywhere on Earth.

```bash
# Transform MLLW to WGS84 ellipsoidal height in Norton Sound, AK
transformez build -R -166/-164/63/64 -E 1s -I vdatum:mllw -O epsg:4979

# Transform a raster directly. Transformez reads the bounds and resolution from the file.
transformez shift my_dem.tif -I vdatum:mllw -O epsg:5703

# Inspect a reference or plan a transformation before running it.
transformez info reference vdatum:mllw
transformez plan -I vdatum:mllw -O epsg:5703 -R -166/-164/63/64
```

From Python:

```python
import transformez

shift_array = transformez.generate_grid(
    region=[80, 85, 10, 15],   # [West, East, South, North]
    increment="3s",
    datum_in="vdatum:mllw",
    datum_out="epsg:4979",
)
```

> ⚠️ Shift grids are always added to your elevation data — the sign conventions are handled internally. See the [methodology guide](https://transformez.readthedocs.io/en/latest/user_guide/methodology.html#the-datum-shift-sign-conventions) for the physical intuition.

## 📚 Documentation

Would you like to know more? Check out the [Official Documentation](https://transformez.readthedocs.io) to learn about:

* **The Python API:** Build custom, memory-safe transformations directly into your applications.
* **Offline Field Ops:** Pre-fetch global FES models, VDatum grids, and NASA coastlines for offline execution (transformez prefetch).
* **Data Provenance:** Learn how Transformez embeds automated metadata tags into output GeoTIFFs for strict scientific traceability.
* **Validation & Accuracy:** Measured agreement against NOAA CO-OPS, NOAA VDatum, FES/DTU, and NGS HTDP.
 g
## ⚖ License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/ciresdem/transformez/blob/main/LICENSE) file for details.

Copyright (c) 2010-2026 Regents of the University of Colorado
