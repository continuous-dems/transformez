import pytest

from transformez.reference.fetcher import GridFetcher, MissingGridError


def test_dist2coast_missing_raises_missing_grid_error(monkeypatch, tmp_path):
    region = ...  # use the standard small test Region fixture here
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
    region = ...  # standard Region fixture
    fetcher = GridFetcher(
        region=region,
        nx=10,
        ny=10,
        cache_dir=tmp_path,
    )

    monkeypatch.setattr(
        fetcher, "_fetch_dist2coast_m", lambda: pytest.fail("not reached")
    )
