"""GridWriter must never expose a partly written grid.

Shift grids live in a shared cache and are rewritten while other threads (and
processes) of the same run read them. Writing in place truncates the file
first, so a concurrent reader could get a missing or incomplete grid; one such
read put a NOS survey ~36 m off in a test DEM. The grid is now written to a
temporary file and moved into place atomically.
"""

import threading

import numpy as np
import pytest
import rasterio
from fetchez.spatial import Region

from transformez.grid import io as grid_io
from transformez.grid.io import GridWriter

REGION = Region(-120.0, -119.0, 33.0, 34.0)


def _grid(value=1.5, size=400):
    return np.full((size, size), value, dtype="float32")


def _leftovers(directory):
    return [
        p.name for p in directory.iterdir() if p.name.startswith(".") or "tmp" in p.name
    ]


def test_write_produces_grid_and_no_temp_files(tmp_path):
    out = GridWriter.write(tmp_path / "shift.tif", _grid(), REGION, tags={"k": "v"})

    with rasterio.open(out) as src:
        assert np.all(src.read(1) == 1.5)
        assert src.tags()["k"] == "v"
    assert _leftovers(tmp_path) == []


def test_concurrent_rewrites_never_expose_a_partial_grid(tmp_path):
    path = tmp_path / "shift.tif"
    data = _grid()
    GridWriter.write(path, data, REGION)
    stop = threading.Event()
    bad_reads = []

    def writer():
        while not stop.is_set():
            GridWriter.write(path, data, REGION)

    def reader():
        for _ in range(150):
            try:
                with rasterio.open(path) as src:
                    arr = src.read(1)
                if arr.shape != data.shape or not np.all(arr == 1.5):
                    bad_reads.append("wrong values")
            except (rasterio.errors.RasterioIOError, OSError, ValueError) as exc:
                bad_reads.append(type(exc).__name__)

    writers = [threading.Thread(target=writer) for _ in range(3)]
    readers = [threading.Thread(target=reader) for _ in range(3)]
    for t in writers + readers:
        t.start()
    for t in readers:
        t.join()
    stop.set()
    for t in writers:
        t.join()

    assert bad_reads == []
    assert _leftovers(tmp_path) == []


def test_failed_write_keeps_existing_grid(tmp_path, monkeypatch):
    path = tmp_path / "shift.tif"
    GridWriter.write(path, _grid(1.5), REGION)
    real_open = grid_io.rasterio.open

    class FailingWrite:
        def __init__(self, *args, **kwargs):
            self._dst = real_open(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self._dst.close()

        def write(self, *args, **kwargs):
            raise RuntimeError("disk full")

    monkeypatch.setattr(grid_io.rasterio, "open", FailingWrite)
    with pytest.raises(RuntimeError):
        GridWriter.write(path, _grid(9.0), REGION)
    monkeypatch.undo()

    with rasterio.open(path) as src:
        assert np.all(src.read(1) == 1.5)
    assert _leftovers(tmp_path) == []
