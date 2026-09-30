import pytest
import zipfile
import numpy as np

from unittest.mock import MagicMock

import fetchez
from fetchez.spatial import Region
from transformez.grid.engine import GridEngine
from transformez.reference.fetcher import GridFetcher, MissingGridError


def test_dist2coast_missing_raises_missing_grid_error(monkeypatch, tmp_path):
    region = Region(-117.5, -117.25, 28.5, 28.75)
    fetcher = GridFetcher(
        region=region,
        nx=10,
        ny=10,
        cache_dir=tmp_path,
    )

    def fake_fetch_grid(module_name, **kwargs):
        assert module_name == "dist2coast"
        return []

    monkeypatch.setattr(fetcher, "fetch_grid", fake_fetch_grid)

    with pytest.raises(MissingGridError, match="Dist2Coast.*unavailable"):
        fetcher._fetch_dist2coast_m()


def test_missing_dist2coast_prevents_coastal_context(monkeypatch, tmp_path):
    region = Region(-117.5, -117.25, 28.5, 28.75)
    fetcher = GridFetcher(
        region=region,
        nx=10,
        ny=10,
        cache_dir=tmp_path,
    )

    monkeypatch.setattr(
        fetcher, "_fetch_dist2coast_m", lambda: pytest.fail("not reached")
    )


def test_fetch_grid_extracts_zip_with_p_f_extract(monkeypatch, tmp_path):
    archive = tmp_path / "datum.zip"
    grid = tmp_path / "datum.gtx"
    grid.write_bytes(b"grid")

    with zipfile.ZipFile(archive, "w") as z:
        z.write(grid, "datum.gtx")

    fetcher = GridFetcher(
        region=Region(-117.5, -117.25, 28.5, 28.75),
        nx=2,
        ny=2,
        cache_dir=tmp_path,
        htdp_tool=MagicMock(),
    )

    monkeypatch.setattr(
        fetchez.api,
        "get",
        lambda **kwargs: [archive],
    )

    seen = {}

    def fake_extract(src, **kwargs):
        seen["src"] = src
        seen["kwargs"] = kwargs
        return [tmp_path / "datum.gtx"]

    monkeypatch.setattr(
        "transformez.reference.fetcher.p_f_extract",
        fake_extract,
    )

    result = fetcher.fetch_grid(
        "vdatum",
        datatype="datum",
        query="datum",
    )

    assert result == [tmp_path / "datum.gtx"]
    assert seen["src"] == archive
    assert seen["kwargs"]["members"] == ["datum", ".met", ".inf"]


def test_fetch_vdatum_model_grid_uses_safe_extraction(
    monkeypatch,
    tmp_path,
):
    archive = tmp_path / "vdatum.zip"
    grid = tmp_path / "CONUSPAC.gtx"
    grid.write_bytes(b"grid")

    class Entry(dict):
        pass

    entry = {
        "dst_fn": str(archive),
        "archive_member": "CONUSPAC.gtx",
    }

    fetcher = GridFetcher(
        region=Region(-117.5, -117.25, 28.5, 28.75),
        nx=2,
        ny=2,
        cache_dir=tmp_path,
        htdp_tool=MagicMock(),
    )

    monkeypatch.setattr(
        fetcher,
        "_fetch_vdatum_entries",
        lambda _: [entry],
    )

    extracted = tmp_path / "CONUSPAC.gtx"
    extracted.write_bytes(b"grid")

    calls = []

    def fake_extract(src, **kwargs):
        calls.append((src, kwargs))
        return [extracted]

    monkeypatch.setattr(
        "transformez.reference.fetcher.p_f_extract",
        fake_extract,
    )

    monkeypatch.setattr(
        GridEngine,
        "load_and_interpolate",
        lambda *args, **kwargs: np.ones((2, 2)),
    )

    result = fetcher._fetch_vdatum_model_grid("xgeoid23")

    assert result.shape == (2, 2)
    assert calls == [
        (
            archive,
            {"outdir": tmp_path, "members": ["CONUSPAC.gtx"]},
        )
    ]
