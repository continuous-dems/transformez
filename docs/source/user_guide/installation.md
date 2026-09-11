# 📦 Installation

## From Conda (Recommended)

Transformez is available on `conda-forge`:

```bash
conda install -c conda-forge transformez
From Pip/PyPI
pip install transformez
```

## From Source

Clone and install in editable mode (useful for development or tracking main):

```bash
git clone https://github.com/continuous-dems/transformez.git
cd transformez
pip install -e ./
```

Or install directly from the repository without cloning:

```bash
pip install git+https://github.com/continuous-dems/transformez.git#egg=transformez
```

## External Engines

Transformez manages its external geodetic engines through the CLI, downloading and configuring them automatically. Neither engine is required for every transformation: Transformez will tell you when a requested pathway needs one.

### HTDP

Transformez uses the NGS Horizontal Time-Dependent Positioning (HTDP) software for transformations involving dynamic reference frames and coordinate-epoch changes. Install it via the Transformez CLI:

```bash
transformez htdp install
```

By default HTDP installs into your user configuration. To install into the current project's cache instead (useful for reproducible project environments):

```bash
transformez htdp install --project
```

If your workflows stay within static tidal/geoid transformations, HTDP may not be needed at all. Transformez will surface a clear message if a requested transformation requires it.

### NOAA VDatum Java

The NOAA VDatum Java engine is only needed for direct VDatum comparison and validation. It can likewise be installed from the Transformez CLI:

```bash
transformez vdatum install
```

> Next up: once installed, head to [Usage](usage.md) to generate your first transformation.
