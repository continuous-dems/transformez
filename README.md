<!-- <p align="center"> -->
<!-- 	<a href="https://github.com/continuous-dems"> -->
<!-- 		<img src="https://github.com/continuous-dems/fetchez/blob/modules/docs/source/_static/continuous_dems_logo.svg" height="80" alt="Continuous DEMs Logo"> -->
<!-- 	</a> -->
<!-- </p> -->
<h1 align="center">Transformez</h1>
<p align="center"><strong>Global vertical datum transformations, simplified.</strong></p>

<p align="center">
  <a href="https://github.com/continuous-dems/transformez"><img src="https://img.shields.io/badge/version-0.3.5-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.12+-yellow.svg" alt="Python"></a>
  <a href="https://badge.fury.io/py/transformez"><img src="https://badge.fury.io/py/transformez.svg" alt="PyPI version"></a>
  <a href="https://cudem.zulip.org"><img src="https://img.shields.io/badge/zulip-join_chat-brightgreen.svg" alt="Project Chat"></a>
</p>

**Transformez** is a standalone Python engine for converting geospatial data between vertical datums (e.g., `MLLW` ↔ `NAVD88` ↔ `Ellipsoid`).

Originally developed as the core transformation engine for the [CUDEM](https://github.com/continuous-dems/cudem) project, Transformez has evolved into a standalone datum transformation suite.

---

### ❓ Why Transformez?

Vertical Datum transformations can cause a lot of confusion and headache when trying to process heterogeneous data from around the world into a single unified vertial reference. 

**Transformez simplifies this process!**

## 📦 Installation

**Install Transformez**
Install the transformez python package:

```bash
pip install transformez
```

**Install HTDP**
The NGS Horizontal Time-Dependent Positioning (HTDP) software is required to perform highly accurate plate tectonic and frame transformations, you can install it with transformez!:

```bash
transformez htdp install
```

## 🐄 Quickstart

**Generate a vertical shift grid for anywhere on Earth.**

```bash
# Transform MLLW to WGS84 Ellipsoid in Norton Sound, AK

transformez grid -R -166/-164/63/64 -E 1s -I mllw -O 4979
```

**Transform a raster directly.** Transformez reads the bounds/resolution from the file.

```bash
transformez raster my_dem.tif -I mllw -O 5703
```

**Integrate directly into your fetchez pipeline.**

```bash
# Download GEBCO and shift EGM96 to WGS84 on the fly
fetchez gebco ... --hook transformez:datum_in=5773,datum_out=4979
```

## 📚 Documentation
Would you like to know more? Check out our [Official Documentation](https://transformez.readthedocs.io) to learn about:

* **The Python API:** Build custom transformation into your apps.

---

## ⚖ License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/ciresdem/transformez/blob/main/LICENSE) file for details.
Copyright (c) 2010-2026 Regents of the University of Colorado
