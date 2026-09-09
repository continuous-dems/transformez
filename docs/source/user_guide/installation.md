# 📦 Installation

## From Conda (Recommended)

* Transformez is available on `conda-forge`:

```bash
conda install -c conda-forge transformez
```

## From Pip/PyPi

```bash
pip install transformez
```

## From Source

Download and install git (If you have not already): [git installation](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

Then,

```bash
pip install git+https://github.com/continuous-dems/transformez.git#egg=transformez
```

Clone and install from source

```bash
git clone https://github.com/continuous-dems/transformez.git
cd transformez
pip install -e ./
```

## Prerequisites and Extras:

### HTDP
Transformez relies on the NGS Horizontal Time-Dependent Positioning (HTDP) software to perform highly accurate plate tectonic and frame transformations.
HTDP is required for transformations that involve supported dynamic reference-frame or coordinate-epoch changes.

You can install HTDP directly from the [transformez cli](cli_usage.md):

```bash
transformez htdp install
```

### NOAA VDatum Java
The NOAA VDatum Java engine is only needed for direct VDatum comparison/validation and can be installed and run directly from the [Transforemz cli](cli_usage.md)

```bash
transformez vdatum install
```

> Next up: once installed, head to [Usage](usage.md) to generate your first transformation.
