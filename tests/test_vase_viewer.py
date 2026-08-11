import numpy as np
import xarray as xr
from shapely.geometry import Polygon

from cubedynamics import pipe, verbs as v
from cubedynamics.plotting import cube_viewer
from cubedynamics.plotting.cube_plot import CubePlot
from cubedynamics.plotting.geom import GeomVaseOutline
from cubedynamics.vase import VaseDefinition, VaseSection


def test_cubeplot_renders_without_vase_outline(tmp_path):
    data = xr.DataArray(
        np.arange(8).reshape(2, 2, 2), dims=("time", "y", "x"), name="demo"
    )

    cube_plot = CubePlot(
        data,
        show_progress=False,
        out_html=str(tmp_path / "plain.html"),
    )

    html = cube_plot.to_html()
    assert "data:image/png" in html


def test_cubeplot_with_vase_outline(tmp_path):
    data = xr.DataArray(
        np.arange(8).reshape(2, 2, 2), dims=("time", "y", "x"), name="demo"
    )
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    vase_def = VaseDefinition([VaseSection(time=0, polygon=square)])

    cube_plot = CubePlot(
        data,
        show_progress=False,
        out_html=str(tmp_path / "vase.html"),
    )

    html = cube_plot.stat_vase(vase_def).geom_vase_outline().to_html()
    assert "data:image/png" in html


def test_vase_chain_with_geom_cube(tmp_path):
    data = xr.DataArray(
        np.arange(8).reshape(2, 2, 2), dims=("time", "y", "x"), name="demo"
    )
    triangle = Polygon([(0, 0), (1, 0), (0.5, 1)])
    vase_def = VaseDefinition([VaseSection(time=0, polygon=triangle)])

    plot_obj = (
        CubePlot(data, show_progress=False, out_html=str(tmp_path / "vase_geom.html"))
        .stat_vase(vase_def)
        .geom_cube()
        .geom_vase_outline(color="limegreen", alpha=0.7)
    )

    html = plot_obj.to_html()
    assert "data:image/png" in html


def test_vase_tint_called_for_each_face(monkeypatch, tmp_path):
    data = xr.DataArray(np.ones((2, 2, 2)), dims=("time", "y", "x"))
    mask = xr.DataArray(np.ones_like(data, dtype=bool), dims=data.dims)

    calls = []

    def record_tint(rgb_arr, mask_slice, color_rgb, alpha):
        calls.append(mask_slice.shape)
        return rgb_arr

    monkeypatch.setattr(cube_viewer, "_apply_vase_tint", record_tint)

    html = cube_viewer.cube_from_dataarray(
        data,
        out_html=str(tmp_path / "faces.html"),
        show_progress=False,
        return_html=True,
        vase_mask=mask,
        vase_outline=GeomVaseOutline(),
        thin_time_factor=1,
    )

    assert "data:image/png" in html
    assert len(calls) == 6


def test_vase_tint_changes_face_pixels(monkeypatch, tmp_path):
    data = xr.DataArray(np.zeros((2, 2, 2)), dims=("time", "y", "x"))
    mask = xr.DataArray(np.ones_like(data, dtype=bool), dims=data.dims)

    captured = []
    original_encoder = cube_viewer._rgba_to_png_base64

    def capture_rgba(rgba):
        captured.append(rgba)
        return original_encoder(rgba)

    monkeypatch.setattr(cube_viewer, "_rgba_to_png_base64", capture_rgba)

    cube_viewer.cube_from_dataarray(
        data,
        out_html=str(tmp_path / "tinted.html"),
        show_progress=False,
        return_html=True,
        vase_mask=mask,
        vase_outline=GeomVaseOutline(color="red", alpha=1.0),
        thin_time_factor=1,
        fill_limits=(-1.0, 1.0),
    )

    assert captured
    baseline_front = cube_viewer._colormap_to_rgba(
        data.isel(time=0).transpose("y", "x").values,
        cmap="viridis",
        fill_limits=(-1.0, 1.0),
    )
    assert not np.array_equal(captured[0], baseline_front)


def test_vase_panels_added_to_viewer_html(tmp_path):
    data = xr.DataArray(np.zeros((4, 8, 8)), dims=("time", "y", "x"), name="panel")

    square = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    smaller = Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)])
    vase_def = VaseDefinition([
        VaseSection(time=0, polygon=square),
        VaseSection(time=3, polygon=smaller),
    ])

    plot_obj = (pipe(data) | v.vase(vase=vase_def, outline=True)).unwrap()
    html = plot_obj.to_html()

    assert "cd-vase-panel" in html
