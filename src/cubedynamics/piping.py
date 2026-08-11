"""Pipe wrapper enabling ``|`` composition for cube operations.

This module is part of the CubeDynamics "grammar-of-cubes":
- Data loaders produce xarray objects (often dask-backed) with dims ``(time, y, x)``.
- Verbs are pipe-friendly transformations: cube → cube (or cube → scalar/plot side-effect).
- Plotting follows a grammar-of-graphics model (aes, geoms, stats, scales, themes).

Canonical API:
- :class:`cubedynamics.piping.Pipe` for wrapping values
- :class:`cubedynamics.piping.Verb` for pipe-aware callables
- :func:`cubedynamics.piping.pipe` convenience constructor
"""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


U = TypeVar("U")


def _attach_viewer(target: Any, viewer: Any) -> None:
    try:
        setattr(target, "_cd_last_viewer", viewer)
        return
    except Exception:
        pass
    try:
        if hasattr(target, "attrs"):
            target.attrs["_cd_last_viewer"] = viewer
    except Exception:
        pass


class Verb(Generic[T, U]):
    """Wrap callables so they can participate in ``pipe`` grammar.

    Grammar contract
    ----------------
    Pipe infrastructure. A :class:`Verb` is pipe-ready and may be called
    directly (``Verb(func)(cube)``) or inserted into a pipe chain
    (``pipe(cube) | Verb(func)``). It preserves whatever laziness or chunking
    semantics the underlying callable provides.

    Parameters
    ----------
    func : Callable[[T], U]
        Callable representing the verb body.

    Returns
    -------
    Verb
        A verb wrapper that can be invoked directly or in a pipe chain.

    Notes
    -----
    The wrapper does not alter execution semantics; it simply forwards to
    ``func``. If ``func`` sets ``_cd_passthrough_on_call`` the original input is
    returned to keep pipe chains flowing without eagerly computing viewers. If a
    verb produces a viewer object, it is attached to the wrapped cube for rich
    notebook displays without forcing computation.

    Examples
    --------
    Direct call:
    >>> from cubedynamics.piping import Verb
    >>> double = Verb(lambda x: x * 2)
    >>> double(3)
    6

    Pipe style:
    >>> from cubedynamics.piping import pipe
    >>> result = (pipe(3) | double).unwrap()
    >>> assert result == 6

    See Also
    --------
    cubedynamics.piping.Pipe, cubedynamics.piping.pipe
    """

    def __init__(self, func: Callable[[T], U]):
        self.func = func

    def __call__(self, value: T) -> U:
        result = self.func(value)
        if getattr(self, "_cd_passthrough_on_call", False):
            _attach_viewer(value, result)
            return value  # type: ignore[return-value]
        return result


class Pipe(Generic[T]):
    """Lightweight wrapper enabling ``|`` composition for cube operations.

    Grammar contract
    ----------------
    Pipe infrastructure. ``Pipe`` itself is not a verb but carries values
    through verb stages and supports direct calls to verbs or plain callables.
    It is both direct-call (``Pipe(value)``) and pipe-ready via the ``|``
    operator.

    Parameters
    ----------
    value : T
        Object to wrap, typically an :class:`xarray.DataArray`,
        :class:`xarray.Dataset`, or streaming :class:`cubedynamics.streaming.VirtualCube`.

    Returns
    -------
    Pipe
        A pipe-ready wrapper exposing ``|`` and ``unwrap``.

    Notes
    -----
    ``Pipe`` preserves streaming objects such as
    :class:`~cubedynamics.streaming.VirtualCube` and does not trigger
    computation. Viewer attachments are stored on the wrapped value when verbs
    mark themselves as pass-through, allowing notebook HTML reprs to show
    inline.

    Examples
    --------
    Direct call:
    >>> from cubedynamics.piping import Pipe
    >>> Pipe(5).unwrap()
    5

    Pipe style:
    >>> from cubedynamics.piping import pipe
    >>> cube = pipe(5) | (lambda v: v + 1)
    >>> cube.unwrap()
    6

    See Also
    --------
    cubedynamics.piping.Verb, cubedynamics.piping.pipe
    """

    def __init__(self, value: T) -> None:
        self.value = value

    def __or__(self, func: Callable[[T], U]) -> "Pipe[U]":
        """Apply ``func`` to the wrapped value and return a new :class:`Pipe`."""

        new_value = func(self.value)
        if getattr(func, "_cd_passthrough_on_pipe", False):
            viewer = new_value
            _attach_viewer(self.value, viewer)
            new_value = self.value
        return Pipe(new_value)

    def unwrap(self) -> T:
        """Return the wrapped value, ending the pipe chain."""

        return self.value

    def __repr__(self) -> str:
        """Return the repr of the wrapped value for plain-text displays."""

        return repr(self.value)

    def _repr_html_(self):
        """Rich HTML representation for Jupyter notebooks."""

        val = self.value
        viewer = getattr(val, "_cd_last_viewer", None)
        if viewer is None:
            viewer = getattr(getattr(val, "attrs", {}), "_cd_last_viewer", None)
        if viewer is not None and hasattr(viewer, "_repr_html_"):
            return viewer._repr_html_()
        if hasattr(val, "_repr_html_"):
            return val._repr_html_()
        return repr(val)

    @property
    def v(self) -> T:
        """Convenience alias for :pyattr:`value`."""

        return self.value


def pipe(value: T) -> Pipe[T]:
    """Wrap ``value`` in a :class:`Pipe` to enable ``Pipe | op(...)`` chaining.

    Grammar contract
    ----------------
    Pipe infrastructure. ``pipe`` is a direct-call helper that returns a
    pipe-ready wrapper and does not modify the underlying object.

    Parameters
    ----------
    value : T
        Input object, often an :class:`xarray.DataArray`, :class:`xarray.Dataset`,
        or :class:`~cubedynamics.streaming.VirtualCube`.

    Returns
    -------
    Pipe
        A :class:`Pipe` carrying ``value``.

    Notes
    -----
    The wrapper preserves streaming/lazy objects and does not compute data. Use
    :py:meth:`Pipe.unwrap` to exit the pipe chain and retrieve the value. Any
    viewer objects created by verbs will be attached to the wrapped value for
    rich HTML display in notebooks.

    Examples
    --------
    Direct call:
    >>> from cubedynamics.piping import pipe
    >>> res = (pipe(1) | (lambda x: x + 2)).unwrap()
    >>> assert res == 3

    See Also
    --------
    cubedynamics.piping.Pipe, cubedynamics.piping.Verb
    """

    return Pipe(value)


__all__ = ["Pipe", "pipe", "Verb"]
