# 🗺️ Vertical References

A reference describes the surface that elevations are expressed relative to. Transformez accepts multiple kinds of vertical input:

| Form                  | Example          | Meaning                            |
| --------------------- | ---------------- | ---------------------------------- |
| Authority CRS         | `EPSG:5703`      | Standard CRS resolved through PROJ |
| Transformez reference | `vdatum:mllw`    | Named physical/model surface       |
| Compound CRS          | `EPSG:4326+5703` | Horizontal + vertical CRS          |

## Namespaced References

Authority-defined CRSs cover heights above a geoid, but tidal and ocean-model surfaces have no standard EPSG definition. Transformez names these custom vertical references with a namespace indicating **who the provider is and where the surface comes from**:

```text
vdatum:mllw # NOAA VDatum Mean Lower Low Water
vdatum:mhw # NOAA VDatum Mean High Water
vdatum:msl # NOAA VDatum Mean Sea Level

global:lat # Global Lowest Astronomical Tide proxy
global:hat # Global Highest Astronomical Tide proxy
global:mss # Global Mean Sea Surface
```


This distinguishes VDatum's realization of MLLW from a global model's realization of LAT, even though both represent similar physical concepts.

## References vs. Bindings

Transformez conceptually separates vertical **references** from vertical **bindings**:

- The **reference** describes *what* the surface is (e.g., NOAA's realization of MLLW).
- The **binding** describes *how* Transformez realizes and operates on that surface.

Bindings encode the realization details, such as `provider`, `engine`, `provider-specific datum`, `native frame`, and `default model`, independently of the reference metadata. This separation lets the same reference evolve to new models or providers without changing user-facing input syntax.

Not all references have a supported binding; see [Models and Providers](providers.md) for the current bindings.

> **Related pages:** [Usage](usage.md) shows references in practice; [Methodology](methodology.md) explains how references are parsed and routed through the transformation engine.
