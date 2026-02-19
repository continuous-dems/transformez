# 🌍 Transformez ↕

**Global vertical datum transformations, simplified.**

*Transformez Les Données*

> 🚀 **v0.2.0:** Now supporting global tidal transformations via FES2014 & SEANOE.

**Transformez** is a standalone Python engine for converting geospatial data between vertical datums (e.g., `MLLW` ↔ `NAVD88` ↔ `Ellipsoid`).

## The Problem
Vertical transformation is a mess.
* **NOAA VDatum** is the gold standard but only covers US coastal waters.
* **Global Models** (like FES2014 or DTU) are locked behind FTPs, logins, or complex scientific formats.
* **Frame Shifts** (NAD83 vs WGS84) are often ignored, leading to 1-2 meter errors in places like Alaska or the Pacific.

## The Solution
**Transformez** acts as a universal broker. It attempts to use the best local authority (NOAA) and automatically falls back to the best global scientific model (FES/HTDP) when local coverage ends.

It is:
* **Open:** Uses 100% open data (NOAA, SEANOE, PROJ). No logins required.
* **Smart:** Automatically handles the "Frame Bridge" between tectonic plates (e.g., transforming WGS84 global tides to NAD83 local geoids).
* **Robust:** Handles dateline crossings (0-360 vs -180/180) and bot-checks automatically.

---

## 🔍 Methodology: The Flow

Transformez uses a **Hub-and-Spoke** architecture centered on **WGS84 (EPSG:4979)**.

```mermaid
graph TD
    A[User Requests: MLLW -> NAVD88] --> B{Is Location in US?}
    B -- Yes --> C[Try NOAA VDatum Grid]
    C --> D{Coverage Found?}
    D -- Yes --> E[Use VDatum Shift]
    D -- No --> F[Global Fallback Mode]
    B -- No --> F

    F --> G[Fetch FES2014 - SEANOE]
    G --> H[Calculate LAT/MSL to Ellipsoid]
    H --> I[Calculate Plate Shift (HTDP)]
    I --> J[Composite Global Shift]

    E --> K[Apply to Data]
    J --> K
```

* Local Check: It first queries NOAA's VDatum grid (via fetchez).

* Global Fallback: If VDatum returns 0 (no coverage), it switches to FES2014 (Finite Element Solution), a global hydrodynamic tide model.

* Frame Harmonization: It detects if your input/output datums are on different tectonic plates (e.g., NAD83 vs ITRF2014). It runs NGS HTDP to calculate the crustal velocity shift (often ~1.5m) and applies it.

* Result: You get a seamless vertical shift grid that is precise near shore (NOAA) and statistically valid in the open ocean (FES).

## Installation

```bash
pip install transformez
```

*Requires [htdp](https://geodesy.noaa.gov/TOOLS/Htdp/Htdp.shtml) to be in your system PATH for frame transformations.*

## Usage

***Generate a vertical shift grid for anywhere on Earth.***

```bash
# Transform MLLW to WGS84 Ellipsoid in Norton Sound, AK
# (Where NOAA has no coverage!)
transformez -R -166/-164/63/64 -E 3s \
    --input-datum mllw \
    --output-datum 4979 \
    --output shift_ak.tif
```

What happens?

- Transformez sees "mllw".

- It checks NOAA VDatum. Coverage Missing.

- It activates Global Fallback.

- It downloads FES2014 from SEANOE.

- It calculates htdp coefficients.

- It calculates: (LAT -> MSL) + (MSL -> WGS84).

- It produces shift_ak.tif.

***Transform a raster directly.*** Transformez reads the bounds/resolution from the file.

```bash
transformez --dem input_bathymetry.tif \
    --input-datum "mllw" \
    --output-datum "5703:geoid=geoid12b" \
    --output output_navd88.tif
```

***Integrate directly into your download pipeline.***

```bash
# Download GEBCO and shift EGM96 to WGS84 on the fly
fetchez gebco ... --hook transformez:datum_in=5773,datum_out=4979
```

## Python API

```python
from transformez.transform import VerticalTransform
from fetchez.spatial import Region

# Define a region in India (Bay of Bengal)
region = Region(80, 85, 10, 15)

# Initialize Transformer
# Requesting "MLLW" in India triggers the Global Fallback automatically
vt = VerticalTransform(
    region=region,
    nx=1000, ny=1000,
    epsg_in="mllw",       # Will resolve to FES2014 LAT
    epsg_out="epsg:4979"  # WGS84 Ellipsoid
)

# Generate Shift
shift, unc = vt._vertical_transform(vt.epsg_in, vt.epsg_out)
```

## Supported Datums

* **Tidal**: mllw, mhhw, msl, lat, hat

* **Ellipsoidal**: 4979 (WGS84), 6319 (NAD83 2011)

* **Orthometric**: 5703 (NAVD88), egm2008, egm96

* **Geoids**: g2018, g2012b, geoid09, xgeoid20b

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/ciresdem/transformez/blob/main/LICENSE) file for details.
Copyright (c) 2010-2026 Regents of the University of Colorado