# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.0.0] - 2026-09-09

### Breaking

* Reworked Transformez around a typed reference → resolution → planning → execution architecture. Standard EPSG CRSs and explicit namespaced references are now the canonical reference model, while legacy datum names (e.g. `mllw`, `msl`, `hat`) remain supported as aliases.
* Reorganized the package into explicit `reference`, `engine`, `grid`, `integration`, and CLI boundaries, with external engines and Fetchez integrations behind dedicated package interfaces.
* Renamed the primary CLI commands to `transformez build` for shift-grid generation and `transformez shift` for raster transformation. Legacy `grid` and `raster` commands remain available as deprecated aliases.

### Added

* **Typed reference system (`transformez.reference`):** centralized parsing and metadata for EPSG, compound, and namespaced references (`vdatum:*`, `global:*`), including compatibility with legacy Transformez/CUDEM reference syntax.
* **Transformation planning:** source and target references are resolved into explicit grid, model, and reference-frame operations that can be inspected before data are fetched or transformations are executed.
* **`ShiftGrid`:** a canonical representation of generated transformations carrying spatial metadata, references, epochs, provenance, cache identity, reprojection support, and direct raster output. `build_shift_grid()` is the canonical grid-generation interface.
* **Reworked NOAA VDatum processing:** each regional coverage package is completed through its native geodetic chain, including modern IGS/xGEOID paths, before normalized coverages are mosaiced according to coverage priority.
* **Physical coastal context:** resolution-independent inland decay based on Dist2Coast distances, with VDatum-aware estuary/river coverage, inland buffers, configurable shoreline extension, and optional unrestricted extrapolation for hydrodynamic modeling.
* **Reference and system inspection:** expanded CLI commands for inspecting references, providers, transformation plans, external engines, and runtime configuration.

### Changed

* Unified the high-level Python API around the same reference-resolution and grid-generation path used by raster, point, component, and standalone-grid transformations.
* Generated-grid cache identity now accounts for references, epochs, region, resolution, coastal behavior, and other generation options.
* Vertical units and other coordinate-reference metadata are now derived from the typed reference model rather than the legacy datum registry.
* Coastal blending and inland decay now use physical Dist2Coast distances rather than pixel-derived distance transforms.

### Fixed

* Fixed VDatum overlap and xGEOID/TSS handling so coverage from different VDatum generations is normalized through its native geodetic path before mosaicing.
* Fixed coastal/global compositing so global proxy surfaces fill missing coastal coverage without redefining the valid tidal-water domain.
* Fixed Dist2Coast processing that could introduce edge artifacts or incorrectly discard zero-valued coastline cells as nodata.
* Fixed HTDP latitude/longitude handling and validated frame transformations against the configured HTDP engine version.

### Deprecated

* Legacy `SRSParser`, `grid`/`raster` CLI aliases, datum aliases, and legacy reference syntax remain supported for compatibility. Explicit EPSG and namespaced references are preferred for new code.

### Validation

* Revalidated tidal, orthometric, global-model, and tectonic transformation paths against NOAA VDatum, NOAA CO-OPS, FES/DTU-derived references, and NGS HTDP.
* Documented expected differences from NOAA VDatum arising from coverage overlap priorities, continuous xGEOID/NAVD88 mosaicing, coastal/global fallback behavior, and differences between external HTDP software versions.
* Expanded regression coverage for reference parsing and planning, VDatum package normalization, coastal compositing, projected rasters, and physical-distance inland decay.

## [0.6.0] - 2026-08-27

### Added

- PointTransformer api class/functionality to be able to transform point clouds directly.
- Comprehensive validation suite (`tests/validation/`) comparing Transformez output against NOAA CO-OPS tide gauges, the VDatum Java CLI, international FES2014 altimetry, and NGS HTDP tectonics.
- Automated Markdown report generation for validation results.
- Pytest configuration for CI/CD integration with `slow` and `accuracy` markers.
- Detailed methodology documentation covering the Hub-and-Spoke model, sign conventions, coastal blending, and inland tidal decay.
- `transformez prefetch` CLI command for offline field use.
- Support for DTU25 MSS baseline alongside FES2014.

### Changed

- **Breaking:** Simplified `VerticalTransform._vertical_transform()` API — removed redundant `epsg_in`/`epsg_out` arguments; the method now uses instance state exclusively. All call sites in `api.py` and `srs.py` updated accordingly.
- Improved error handling in `vdatum.py`: structured Java availability checks, graceful degradation when JAR is missing.
- Refined `RasterQuery` in `utils.py` to handle longitude normalization (`[-180, 180]`) more robustly.
- Consolidated `GridGen` class into `grid_engine.py`; `gridgen.py` is now a deprecated stub.
- Standardized docstrings (Args/Returns format) across all public methods.
- Expanded type hint coverage to 100% of public APIs across all modules.
- Updated documentation index to highlight the Continuous DEMs Project.
- Dynamic blur distance in `GridEngine.fill_nans()` — blur sigma now scales with `decay_pixels` instead of using a hardcoded value.

### Fixed

- Fixed file extension matching in `hooks.py` (`.las` → `".laz", ".las"`).
- Fixed circular import risk in `srs.py` by deferring `VerticalTransform` import to method level.
- Fixed None-safety crashes in `transform.py` when EPSG codes or `SURFACES` entries are missing.
- Removed duplicate `fetch_grid_()` method from `transform.py`.
- Removed deprecated `_get_global_chain_depreciated()` method.
- Pruned all commented-out dead code across the codebase.
- Fixed `vdatum.py` `run_cmd` calls that previously suppressed stderr.
- Fixed HTDP `run_cmd` error handling to catch `CalledProcessError` specifically.

### Removed

- Duplicate `GridGen` class definition (top-level in `grid_engine.py`).
- Dead/deprecated code blocks in `grid_engine.py`, `transform.py`, and `htdp.py`.

## [0.4.4] - 2026-06-25

### Added
- support for projected input rasters in the raster command
- add 'save_shift' to transform_raster api/cli

### CHANGED
- rety failed downloads, such as FES

## [0.4.3] - 2026-05-04

### Added
- new logo
- force htdp 3.5.0

## [0.3.5] - 2026-04-08

### Added

- RTD documentation
- Validation scripts and docs

### Changed

- Vdatum grid ordering (small->large)
- FES -> navd88 when merging with vdatum

## [0.3.4] - 2026-04-06

### Added

- HAT as proxy for mhw (symmetry method)
- Unit conversions in api/cli

### Changed

- Split cli 'run' command into 'grid' and 'raster'

## [0.3.2] - 2026-03-27

### Added
- support for FES2014
- Coastal blend where vdatum cuts off
- decay extrapolation to 0 inland from tidal datums
- Add API

### Changed
- cli now uses click

<...missed...>

## [0.1.0] - 2026-02-10
### Added

### Changed
- Now uses raserio
- Renamed project to `transformez`.
- Refactored and decoupled from old cudem.vdatums
