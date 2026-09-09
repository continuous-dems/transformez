Developer API
=============

The high-level Python API for generating and applying vertical transformation shift grids.

Most users only need three functions — [`generate_grid`](#transformez.api.generate_grid) for shift arrays, [`transform_raster`](#transformez.api.transform_raster) for direct raster transformation, and [`prefetch_region`](#transformez.api.prefetch_region) for offline use — plus the [`ShiftGrid`](#transformez.grid.shift.ShiftGrid) object for fully georeferenced transformation products. All of these are importable directly from the top-level package:

```python
import transformez
transformez.generate_grid(...)
transformez.build_shift_grid(...)
```

A few conventions apply across the API:

* **Inputs are references.** All datum_in / datum_out arguments accept authority CRSs (`EPSG:5703`), namespaced references (`vdatum:mllw`, `global:lat`), or compound forms (`EPSG:4326+5703`). See [Vertical References](/user_guide/references.md).
* **Shift grids are always added** to elevation data — the sign conventions are handled internally. See [sign conventions](/user_guide/methodology.md#the-datum-shift-sign-conventions) before applying a grid manually.
* **Coastal decay is on by default.** Pass `extrapolate_inland=True` (or the CLI equivalent) for hydrodynamic workflows needing unrestricted inland extrapolation.

For worked examples of each entry point, see the [Usage guide](/user_guide/usage.md).


```{eval-rst}
.. automodule:: transformez.api
   :members: generate_grid, transform_raster, prefetch_region
   :undoc-members:
   :show-inheritance:
.. autoclass:: transformez.grid.shift.ShiftGrid
.. autoclass:: transformez.utils.RasterQuery
.. autoclass:: transformez.reference.types.ParsedReference
.. autoclass:: transformez.reference.types.VerticalReference
.. autoclass:: transformez.reference.types.VerticalKind
.. autoclass:: transformez.reference.types.AxisDirection
.. autoclass:: transformez.progress.ProgressEvent
```
