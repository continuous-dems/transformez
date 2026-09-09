# 💻 Command Line Interface

The `transformez` command line tool lets you generate or apply vertical transformation grids. Commands follow the 1.0 architecture: `build` for shift-grid generation, `shift` for raster transformation, plus inspection and planning commands to examine references and transformation paths before running them.

Commands are organized into three groups: **Execution** (`build`, `shift`, `prefetch`), **Discovery** (`list`, `info`, `plan`), and **External engines** (`htdp`, `vdatum` for installing and managing the NGS HTDP and NOAA VDatum engines). Legacy commands `grid` and `raster` remain available as deprecated aliases for `build` and `shift`.

```{eval-rst}
.. click:: transformez.cli:transformez_cli
   :nested: full
   :prog: transformez
```
