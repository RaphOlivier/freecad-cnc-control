"""FreeCAD-specific adapter layer (the only package that imports FreeCAD)."""

from freecad.cnc_control.freecad_adapter.host import (
    FreeCADHost,
    attach_dock,
    translate,
)

__all__ = ["FreeCADHost", "attach_dock", "translate"]
