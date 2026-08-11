import io
import geopandas as gpd
import pytest
import requests
import zipfile
from shapely.geometry import Point

from cubedynamics import fire_time_hull


def test_load_fired_missing_cache_download_disabled(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        fire_time_hull.load_fired_conus_ak(
            which="daily", prefer="gpkg", cache_dir=cache_dir, download=False
        )


def test_load_fired_downloads_and_reads(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    called = {}

    def fake_download(**kwargs):
        called.update(kwargs)
        out = kwargs["out_path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("stub")

    gdf = gpd.GeoDataFrame(
        {"value": [1]}, geometry=[Point(0, 0)], crs="EPSG:3857"
    )

    def fake_read(path):
        called["read_path"] = path
        return gdf

    monkeypatch.setattr(
        fire_time_hull, "_download_and_extract_fired_to_cache", fake_download
    )
    monkeypatch.setattr(gpd, "read_file", fake_read)

    loaded = fire_time_hull.load_fired_conus_ak(
        which="daily",
        prefer="gpkg",
        cache_dir=cache_dir,
        download=True,
        dataset_page="https://example.com/landing",
        download_id="abc123",
        timeout=5,
    )

    assert called["which"] == "daily"
    assert called["prefer"] == "gpkg"
    assert called["dataset_page"] == "https://example.com/landing"
    assert called["download_id"] == "abc123"
    assert called["timeout"] == 5
    assert called["out_path"].name.endswith(".gpkg")
    assert called["read_path"].name.endswith(".gpkg")
    assert isinstance(loaded, gpd.GeoDataFrame)
    assert loaded.crs.to_string() == "EPSG:4326"
    assert loaded.equals(gdf.to_crs("EPSG:4326"))


def test_download_tolerates_landing_page_403(monkeypatch, tmp_path):
    which = "daily"
    prefer = "gpkg"
    dataset_page = "https://scholar.colorado.edu/concern/datasets/d504rm74m"
    download_id = "h702q749s"
    primary_name = fire_time_hull._FIRED_FILE_MAP[(which, prefer)]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(primary_name, "payload")
    zip_bytes = buf.getvalue()

    calls = []

    class FakeResponse:
        def __init__(self, *, status_code, headers=None, content=b""):
            self.status_code = status_code
            self.headers = headers or {}
            self._content = content

        def iter_content(self, chunk_size):
            yield self._content

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"HTTP {self.status_code}")

    class FakeSession:
        def __init__(self):
            self.calls = calls

        def get(self, url, headers=None, **kwargs):
            self.calls.append({"url": url, "headers": headers})
            if len(self.calls) == 1:
                return FakeResponse(status_code=403)
            return FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/zip"},
                content=zip_bytes,
            )

    monkeypatch.setattr(fire_time_hull.requests, "Session", FakeSession)

    out_path = tmp_path / "cache" / primary_name
    with pytest.warns(UserWarning, match="FIRED landing page returned HTTP 403"):
        fire_time_hull._download_and_extract_fired_to_cache(
            which=which,
            prefer=prefer,
            out_path=out_path,
            dataset_page=dataset_page,
            download_id=download_id,
            timeout=1,
        )

    assert len(calls) == 2
    assert calls[0]["url"] == dataset_page
    assert calls[1]["url"].endswith(download_id)
    for call in calls:
        assert call["headers"]["Referer"] == dataset_page
        assert "User-Agent" in call["headers"]
    assert out_path.exists()
    assert out_path.read_text() == "payload"
