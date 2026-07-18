# 📐 Geodetic Methodology & Architecture
To provide survey-grade vertical transformations across massive geographic extents, `transformez` relies on a dynamic, mathematically rigorous architecture.
We do not use hard-coded, point-to-point translation matrices; instead, the engine computes optimal geodetic pathways on the fly.

Here is a look under the hood at how transformez handles complex vertical math.

**1. The Dynamic Hub-and-Spoke Model**
Traditional transformation tools often struggle when routing complex, multi-step conversions (e.g., moving from a local tidal datum directly to a global geoid). `transformez` solves this using an autonomous "Hub-and-Spoke" routing system.

* **Native Ellipsoid Hubs:** Every transformation is mathematically routed through a central geodetic frame (the "Hub").

* **Intelligent Routing:** The engine evaluates the requested input and output datums and automatically selects the safest hub.
For example, if both datums belong to the North American Datum family, the engine routes strictly through the NAD83 ellipsoid hub to avoid introducing unnecessary global transformation errors. If the request crosses international or global boundaries, it scales up to the WGS84 hub.

**2. The Datum Shift Paradox (Sign Conventions)**
A common point of confusion in vertical geodesy is the sign convention of shift grids. It is easy to assume that shifting "up" to a higher surface should result in positive shift values, but physically, the opposite is true.

* **The Stick Analogy:** Imagine standing in the water holding a measuring stick. If you move your "zero" mark to a higher datum (e.g., moving from Mean Sea Level up to Mean Higher High Water), the water level on your stick will read as a lower number.

* **The Rule of Addition:** Because of this, shifting to a higher reference surface actually requires a negative shift value. `transformez` automatically handles these complex sign inversions internally so you don't have to overthink it. You always simply *ADD* the generated shift grid to your raster (i.e., New_DEM = Old_DEM + Shift_Grid). The grid's native positive and negative values automatically ensure the math reflects physical reality.

**3. Continuous Coastal Blending**
Official tidal models (like NOAA's VDatum) only provide data close to the coast. However, modern hydrodynamic modeling requires continuous grids that extend far into the deep ocean.

* **Offshore Extrapolation:** When a requested bounding box extends beyond native VDatum coverage, transformez automatically fetches global satellite altimetry (like FES2014) as a proxy.

* **Smart Blending:** To prevent harsh mathematical steps between the two models, the engine applies a dynamic spatial crossfade, isolating the Mean Dynamic Topography (MDT) and smoothly blending the VDatum boundary into the global satellite frame.

**4. Inland Tidal Decay (The Voronoi-Hermite Method)**
Water levels (and their associated tidal datums) do not physically exist on dry land. However, coastal DEMs require inland datum extrapolation to allow storm surges to properly push water uphill during flood simulations.

* **Voronoi Ridges:** To extrapolate tidal datums inland without introducing artificial slopes, `transformez` generates nearest-neighbor Voronoi ridges from the coastline.

* **Gaussian Blurring & Easing:** These ridges are then heavily blurred and crossfaded with the raw coastal data to ensure $C^1$ continuity (a perfectly smooth mathematical surface with no sharp corners) deep inland.

* **Hermite S-Curve:** Users can dictate how far tidal influences push inland using the `--decay-pixels` parameter. Instead of a harsh linear drop-off, the engine applies a Hermite S-Curve polynomial (where $d$ is the linear decay factor):$$decay = d^2(3 - 2d)$$
This ensures the tidal datum smoothly flattens out into the geodetic baseline exactly where the modeler requires it.

**5. Autonomous Self-Healing**
Geospatial APIs and legacy models are notoriously brittle. `transformez` is designed to survive infrastructure failures silently:

* **Geoid Fallbacks:** If a requested geoid (like g2018) lacks physical coverage in a remote area (e.g., parts of Alaska), the engine automatically scans its registry and downgrades to the newest compatible model (like g2012b or geoid09) to keep the pipeline alive.

* **Tectonic Fallbacks:** When querying the NGS HTDP (Horizontal Time-Dependent Positioning) engine for complex plate tectonic shifts, requests crossing certain temporal epochs can fail. transformez catches these failures and seamlessly falls back to a static datum shift at the target epoch.
