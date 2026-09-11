# 🧰 Models and Providers

Transformez automatically fetches model and reference data from a number of providers, and routes each transformation through whichever provider realizes the requested reference.

| Provider/model  | Role                       | Typical references         |
| --------------- | -------------------------- | -------------------------- |
| NOAA VDatum     | Regional tidal/orthometric | `vdatum:*`                 |
| NGS geoid grids | Orthometric ↔ ellipsoidal  | `EPSG:5703`, etc.          |
| FES             | Global tidal               | `global:lat`, `global:hat` |
| DTU             | Global MSS                 | `global:mss`               |
| Dist2Coast      | Coastal context            | internal                   |
| HTDP            | Frame/epoch                | ellipsoidal frame changes  |

Data fetching, retry, and caching are handled by [Fetchez](https://fetchez.readthedocs.io/en/latest/index.html), so providers can be swapped or extended without touching the transformation engine itself. See [Methodology](methodology.md) for how these models are composed into a single transformation pathway.
