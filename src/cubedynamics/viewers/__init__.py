from .cube_viewer import write_cube_viewer


def simple_cube_widget(*args, **kwargs):
    """Lazy wrapper for the optional ipywidgets-based cube widget."""

    from .simple_plot import simple_cube_widget as _simple_cube_widget

    return _simple_cube_widget(*args, **kwargs)

__all__ = ["simple_cube_widget", "write_cube_viewer"]
