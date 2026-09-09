# 🌊 VDatum Coverage Chains (Appendix)

NOAA VDatum regional packages are treated by Transformez as coherent transformation units rather than as collections of interchangeable grids.

This distinction is important because different generations of VDatum coverage do not necessarily use the same geodetic reference path. In particular, the meaning of the TSS surface depends on the horizontal reference frame recorded in the coverage metadata.

Older regional VDatum models commonly use an NAD83-based path in which the TSS surface is tied to NAVD88. More recent models may instead use IGS-based reference frames and modern xGEOID surfaces.

As a result, Transformez does not independently mosaic all tidal grids and all TSS grids before combining them. Doing so could mix surfaces from different VDatum generations that have different reference semantics.

Instead, each intersecting VDatum coverage is processed independently.

For a requested tidal datum such as `vdatum:mllw`, Transformez:

1. identifies all VDatum coverage packages that intersect the requested region;
2. pairs the requested tidal grid with the matching TSS grid from the same coverage package;
3. reads the coverage metadata to determine the TSS reference path;
4. completes the transformation chain for that coverage in its native reference system;
5. normalizes the resulting shift to the common Transformez working reference;
6. mosaics the normalized coverage with other normalized VDatum coverages according to coverage priority.

Only after this normalization are different VDatum generations allowed to overlap or fill gaps in one another.

## Legacy NAD83 / NAVD88 coverages

For legacy VDatum packages whose metadata reports an NAD83 horizontal frame, the TSS surface is treated as the LMSL-to-NAVD88 relationship.

For a tidal datum such as MLLW, the local hydrographic component is therefore:

```text
MLLW -> LMSL -> NAVD88
```

which is evaluated from the paired tidal and TSS grids as:

```text
tidal_grid - tss_grid
```

This produces a shift already expressed relative to the common NAVD88-like hydrographic working surface used by the coastal compositor.

## Modern IGS / xGEOID coverages

More recent VDatum packages may use an IGS-based reference frame.

For example, an IGS14 coverage uses xGEOID20B rather than directly tying TSS to NAVD88. The coverage must therefore be completed through its native xGEOID and ellipsoidal frame before it can be compared with older VDatum data.

Conceptually, the chain is:

```text
Tidal datum
    -> LMSL / TSS
    -> xGEOID20B
    -> IGS14 ellipsoid
    -> canonical Transformez ellipsoidal frame
    -> canonical hydrographic working surface
```

Transformez performs the appropriate HTDP frame transformation as part of this normalization. The same architecture supports other VDatum roadmaps, such as IGS08 coverages associated with xGEOID17B.

## Coverage mosaicing

Once each coverage has been normalized to the same working reference, Transformez builds a priority mosaic.

Coverage priority is determined from the VDatum release metadata, with newer coverage preferred over older coverage. Lower-priority packages are used only to extend the spatial coverage where higher-priority data are unavailable. This allows a recent regional VDatum model to be preferred in its valid domain while an older regional model still fills a genuine coverage gap outside that domain.

Very small lower-priority contributions are ignored so that isolated fringe pixels from older models do not appear through minor differences in coverage masks or shoreline boundaries.

This priority behavior is applied only after each coverage has been fully normalized. Raw grids from different VDatum generations are never allowed to compete directly.

## Coastal and global fallback

The completed VDatum mosaic represents the best available NOAA regional transformation surface for the requested area.

Where VDatum coverage remains unavailable, Transformez continues the transformation using its coastal/global fallback model. The normalized VDatum surface is combined with the configured global proxy using coastline-aware blending, and inland behavior is handled by the normal Transformez decay model.

The overall processing order is therefore:

```text
VDatum coverage package
    -> paired tidal + TSS grids
    -> coverage-specific geodetic normalization
    -> priority mosaic of normalized coverages
    -> coastal/global fallback
    -> final geoid / reference transformation
```

This preserves the geodetic provenance of each NOAA VDatum generation while still allowing overlapping regional datasets to form a continuous transformation surface.

> Back to the main guide: [Methodology](methodology.md)
