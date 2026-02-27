# 🌍 Transformez ↕

**Global vertical datum transformations, simplified.**

*Transformez Les Données*

> 🚀 **v0.2.2:** Now supporting global tidal transformations via FES2014 & SEANOE.

**Transformez** is a standalone Python engine for converting geospatial data between vertical datums (e.g., `MLLW` ↔ `NAVD88` ↔ `Ellipsoid`).

---

## Installation

### Prerequisites: HTDP
Transformez relies on the NGS Horizontal Time-Dependent Positioning (HTDP) software to perform highly accurate plate tectonic and frame transformations. **You must install this separately.**

**For Windows:**
1. Download the pre-compiled executable (`htdp.exe`) directly from the [NOAA HTDP page](https://geodesy.noaa.gov/TOOLS/Htdp/Htdp.shtml).
2. Place `htdp.exe` in a directory that is in your system's `PATH` (e.g., `C:\Windows\System32` or a custom scripts folder).

**For Linux / macOS:**
You will need a Fortran compiler (like `gfortran`) to compile the source code.
```bash
# 1. Download the Fortran source code
wget [https://geodesy.noaa.gov/TOOLS/Htdp/HTDP-download.zip](https://geodesy.noaa.gov/TOOLS/Htdp/HTDP-download.zip)
unzip HTDP-download.zip

# 2. Compile it
gfortran -o htdp htdp.f

# 3. Move it to your PATH
sudo mv htdp /usr/local/bin/
Install Transformez
Once HTDP is accessible in your terminal, install the python package:

```bash
pip install transformez
```

*Requires [htdp](https://geodesy.noaa.gov/TOOLS/Htdp/Htdp.shtml) to be in your system PATH for frame transformations.*

## Usage

**Generate a vertical shift grid for anywhere on Earth.**

```bash
# Transform MLLW to WGS84 Ellipsoid in Norton Sound, AK
# (Where NOAA has no coverage!)
transformez -R -166/-164/63/64 -E 3s \
    --input-datum mllw \
    --output-datum 4979 \
    --output shift_ak.tif
```

**Transform a raster directly.** Transformez reads the bounds/resolution from the file.

```bash
transformez --dem input_bathymetry.tif \
    --input-datum "mllw" \
    --output-datum "5703:geoid=geoid12b" \
    --output output_navd88.tif
```

**Integrate directly into your download pipeline.**

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

* **Tidal**: mllw, mhhw, msl, lat

* **Ellipsoidal**: 4979 (WGS84), 6319 (NAD83 2011)

* **Orthometric**: 5703 (NAVD88), egm2008, egm96

* **Geoids**: g2018, g2012b, geoid09, xgeoid20b

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/ciresdem/transformez/blob/main/LICENSE) file for details.
Copyright (c) 2010-2026 Regents of the University of Colorado