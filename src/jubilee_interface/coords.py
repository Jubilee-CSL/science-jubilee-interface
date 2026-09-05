"""
=========================================================================================
Fichier : coords.py
Description : Single source of truth for canvas <-> machine coordinate transforms.

Canvas convention (Tkinter):
    origin at top-left of the plateau rectangle; +X points right, +Y points down.
    Units: pixels.

Machine convention (Jubilee deck):
    origin at bottom-left of the plateau when looking down at the machine;
    +X is the vertical direction on canvas (upward), +Y is horizontal (rightward).
    Units: millimetres.

The transform between the two is a 90 degree rotation around Z followed by
pixel <-> mm scaling.  Historically this was implemented as an axis swap
followed by ``_rotate_point_z90_centered`` in ``exporter.py`` and the SCAD
exporter.  Both are now folded into a single, tested step here.  Any output
artefact (``deck.json``, ``experience.json``, DXF, G-code, SCAD/STL) that
carries machine coordinates goes through :func:`canvas_bbox_to_machine_mm`;
any consumer that needs to place something back on the canvas goes through
:func:`machine_bbox_to_canvas_topleft_px`.
=========================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass

from jubilee_interface.constants import PLATEAU_H_MM, PLATEAU_W_MM


@dataclass(frozen=True)
class PlateauFrame:
    """Canvas rectangle occupied by the plateau, plus derived scale factors."""

    x0_px: float
    y0_px: float
    x1_px: float
    y1_px: float
    plateau_w_mm: float = PLATEAU_W_MM
    plateau_h_mm: float = PLATEAU_H_MM

    @property
    def scale_x(self) -> float:
        """mm per pixel along the canvas X (horizontal) axis."""
        return self.plateau_w_mm / (self.x1_px - self.x0_px)

    @property
    def scale_y(self) -> float:
        """mm per pixel along the canvas Y (vertical) axis."""
        return self.plateau_h_mm / (self.y1_px - self.y0_px)

    @classmethod
    def from_canvas(cls, canvas, plateau_id) -> "PlateauFrame":
        x0, y0, x1, y1 = canvas.coords(plateau_id)
        return cls(x0, y0, x1, y1)


@dataclass(frozen=True)
class MachineBBox:
    """Axis-aligned bounding box of a labware, in machine millimetres.

    ``x_mm``/``y_mm`` is the min corner (matches the ``coordinates`` /
    ``offset`` values written into ``experience.json`` and ``deck.json``).
    ``length_mm`` is the extent along the machine X axis; ``width_mm`` is
    the extent along the machine Y axis.
    """

    x_mm: float
    y_mm: float
    length_mm: float
    width_mm: float


def canvas_bbox_to_machine_mm(
    canvas_bbox_px: tuple[float, float, float, float],
    frame: PlateauFrame,
) -> MachineBBox:
    """Map a canvas bounding box ``(cx1, cy1, cx2, cy2)`` to machine mm.

    Applies the canvas->machine axis swap AND the 90 degree rotation around Z
    that aligns +canvas_X with -machine_X.
    """
    cx1, cy1, cx2, cy2 = canvas_bbox_px

    # Canvas -> intermediate (swapped) machine coords, in mm.
    y_swap = (cx1 - frame.x0_px) * frame.scale_x
    x_swap = (cy1 - frame.y0_px) * frame.scale_y
    y_extent = (cx2 - cx1) * frame.scale_x   # along swapped Y
    x_extent = (cy2 - cy1) * frame.scale_y   # along swapped X

    # 90 degree rotation around Z centred on the plateau: (x, y) -> (W - y, x).
    corners = [
        (x_swap, y_swap),
        (x_swap + x_extent, y_swap),
        (x_swap + x_extent, y_swap + y_extent),
        (x_swap, y_swap + y_extent),
    ]
    rotated = [(frame.plateau_w_mm - py, px) for px, py in corners]
    rx = min(p[0] for p in rotated)
    ry = min(p[1] for p in rotated)

    # After the 90 degree rotation, the roles of X/Y extent swap.
    return MachineBBox(
        x_mm=round(rx, 2),
        y_mm=round(ry, 2),
        length_mm=round(y_extent, 2),
        width_mm=round(x_extent, 2),
    )


def machine_bbox_to_canvas_topleft_px(
    bbox: MachineBBox,
    frame: PlateauFrame,
) -> tuple[float, float]:
    """Inverse of :func:`canvas_bbox_to_machine_mm`.

    Returns the top-left ``(cx1, cy1)`` canvas coordinate for a labware whose
    machine-mm bounding box is ``bbox``.  The extents are not returned; the
    caller reconstructs them from the labware definition (or from
    ``bbox.length_mm`` / ``bbox.width_mm``).
    """
    # Invert the 90 degree rotation: (rx, ry) came from (ry, W - rx - y_extent)
    # in the intermediate swapped frame.
    x_swap = bbox.y_mm
    y_swap = frame.plateau_w_mm - bbox.x_mm - bbox.length_mm

    cx1 = frame.x0_px + y_swap / frame.scale_x
    cy1 = frame.y0_px + x_swap / frame.scale_y
    return cx1, cy1


def machine_point_to_dxf(
    x_mm: float,
    y_mm: float,
    plateau_w_mm: float = PLATEAU_W_MM,
    plateau_h_mm: float = PLATEAU_H_MM,
) -> tuple[float, float]:
    """Map a machine-mm point to the DXF plotting convention.

    The DXF layout shows the plateau as it would appear on a laser cutter's
    bed: DXF X goes right, DXF Y goes up, origin at bottom-left.  Since
    machine coordinates now come out of :func:`canvas_bbox_to_machine_mm`,
    this is a straight rectangular flip: ``(x, y) -> (W - x, H - y)``.
    """
    return plateau_w_mm - x_mm, plateau_h_mm - y_mm
