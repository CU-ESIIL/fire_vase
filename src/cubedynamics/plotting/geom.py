from dataclasses import dataclass


@dataclass
class GeomVaseOutline:
    """
    Grammar-of-graphics geom that indicates vase overlays should be applied
    on cube faces during viewer rendering.

    The geom itself does not draw; it simply signals to the cube viewer that
    ``CubePlot.vase_mask`` should be sliced per face and tinted using the
    provided ``color``/``alpha``.
    """

    color: str = "limegreen"
    alpha: float = 0.6
