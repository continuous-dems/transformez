# User Guide

Welcome to the Transformez user guide! Here you will find everything you need to know to install, configure, and run Transformez.

## The Inland Decay Philosophy
Tidal datums (like Mean Higher High Water) physically cease to exist where the ocean meets the land. If a standard GIS user transforms a county-wide DEM to MLLW, they do not want a 2-meter vertical shift mathematically applied 50 miles inland to the top of a mountain.

To protect inland topography, transformez uses a default decay_pixels=100 safety buffer. Using Nearest-Neighbor distance transforms and Hermite smoothing, the engine seamlessly ramps the tidal shift down to zero as it moves inland, successfully anchoring the deep inland terrain back to the geodetic frame (e.g., NAVD88).

* The Modeling Exception:
Hydrodynamic modelers (Tsunami, Storm Surge, Sea Level Rise) are the exception to this rule. To simulate a wave riding up the terrain, the mathematical offset between the geodetic frame and the tidal frame must be preserved infinitely inland. If you are running a hydrodynamic simulation, always pass `--decay-pixels 0` to disable the decay and generate a continuous extrapolation surface.

```{toctree}
:maxdepth: 2

validation
```
