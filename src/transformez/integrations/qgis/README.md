# Transformez QGIS plugin draft

This plugin generates a Transformez reference-to-reference vertical shift grid for the current QGIS map extent, writes it to GeoTIFF, and adds the result to the project.

The subprocess worker calls the public `transformez.api.generate_grid()` interface. Reference parsing, transformation planning, VDatum coverage selection, xGEOID/frame normalization, mosaicing, coastal blending, and provenance therefore remain inside Transformez rather than being duplicated in the QGIS plugin.

## Runtime isolation

Transformez runs in an isolated virtual environment outside the plugin directory:

```text
<QGIS profile>/transformez/runtime/
```

Keeping the runtime outside `python/plugins/transformez_qgis` prevents Rasterio/GDAL conflicts with QGIS and lets QGIS remove or upgrade the plugin without recursively deleting an active virtual environment.

## Logging and progress

Structured Transformez progress is used for the QGIS task progress indicator. Normal subprocess logging is forwarded to the **Transformez** tab in **View > Panels > Log Messages**.

Terminal-only formatting is normalized before logging:

- ANSI color/control sequences are removed.
- carriage-return redraws are collapsed;
- tqdm-style progress bars are suppressed, because their progress is represented by the QGIS task instead.

## Development reloads

When developing by repeatedly replacing the plugin files, QGIS may retain the already-loaded Python module until it is reloaded. QGIS recommends the **Plugin Reloader** plugin for this workflow. A full QGIS restart should not be necessary when using Plugin Reloader.

For normal installation from QGIS Plugin Manager / Install from ZIP, the plugin lives in the active profile's `python/plugins` directory. The isolated Transformez runtime persists separately across plugin updates and uninstalls.

## Managing the Transformez runtime

The plugin menu includes **Transformez -> Manage Runtime...**. This can be used at
any time to inspect the currently installed Transformez version and isolated runtime
path, then reinstall or upgrade Transformez either from PyPI or from a local source
checkout. Runtime updates run as a background QGIS task.

When runtime installation is triggered automatically because **Build Shift Grid...**
finds no usable runtime, the plugin continues to the shift-grid dialog after a
successful install. Updates started explicitly from **Manage Runtime...** simply
report success and leave the plugin ready for use.
