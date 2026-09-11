# User Guide

This guide covers everything you need to install, use, and understand Transformez; from your first shift grid to the geodetic reasoning behind it.

Transformez transforms raster elevations between vertical datums (tidal datums, geoids, and ellipsoids) anywhere on Earth. Transformez resolves your input and output [references](references.md), plans the optimal geodetic pathway, and produces a **spatially varying shift grid** that you can generate from the [CLI](usage.md#command-line-interface), build through the Python API, or apply directly to a raster.

## How to read this guide

- **New to Transformez?** Follow the guide in order: [Installation](installation.md) → [Usage](usage.md) → [References](references.md) → [Methodology](methodology.md).
- **Just want the commands?** Jump to [Usage](usage.md) for CLI and Python examples, or the [full CLI reference](cli_usage.md).
- **Unsure what `-I vdatum:mllw` means?** See [Vertical References](references.md) for authority CRSs, namespaced surfaces, and the reference/binding model.
- **Applying a shift grid to your own data?** Read the [sign conventions](methodology.md#the-datum-shift-sign-conventions) first: the generated shift grid is always **added**.
- **Building flood or surge models?** The [inland decay](methodology.md#inland-tidal-decay) section covers when to disable coastal attenuation.
- **Curious how a tidal-to-geoid pathway is actually built?** [Methodology](methodology.md) explains the hub-and-spoke routing, and the [VDatum Coverage Chains](vdatum_chains.md) appendix goes deep on mixed-generation VDatum handling.
- **Need to trust the numbers?** [Validation & Accuracy](validation.md) shows measured agreement against NOAA CO-OPS, VDatum, FES/DTU, and NGS HTDP.


> Using Transformez from another application? Transformez integrates with Fetchez and QGIS; see the [Integrations](usage.md#integrations) section.


```{toctree}
:maxdepth: 2

installation
usage
cli_usage
references
methodology
vdatum_chains
providers
validation
```
