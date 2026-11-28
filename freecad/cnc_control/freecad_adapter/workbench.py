"""FreeCAD workbench registration and docked-panel lifecycle.

This is the only module that touches ``FreeCADGui``; the GUI and core packages
stay independent of FreeCAD. When FreeCAD is absent (tests), the workbench
base class falls back to ``object`` so lifecycle code can still be tested.
"""

from pathlib import Path

from freecad.cnc_control.freecad_adapter.cam import post_process_selected_job
from freecad.cnc_control.freecad_adapter.commands import SendJobCommand, command_name
from freecad.cnc_control.freecad_adapter.host import FreeCADHost, attach_dock, translate
from freecad.cnc_control.freecad_adapter.qt import QtWidgets
from freecad.cnc_control.gui.panel import CncControlPanel
from freecad.cnc_control.gui.worker_bridge import WorkerBridge

try:  # pragma: no cover - exercised inside FreeCAD
    import FreeCADGui as _FreeCADGui  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - outside FreeCAD
    _FreeCADGui = None

_WorkbenchBase = _FreeCADGui.Workbench if _FreeCADGui is not None else object
_ICON = Path(__file__).resolve().parents[1] / "resources" / "icons" / "CNCControl.svg"


class CncControlWorkbench(_WorkbenchBase):
    """Minimal workbench that owns the docked control panel."""

    MenuText = translate("CncControl", "CNC Control")
    ToolTip = translate("CncControl", "Drive GRBL 1.1 controllers from FreeCAD")
    Icon = str(_ICON)

    def __init__(self, host=None, bridge_factory=None) -> None:
        super().__init__()
        self._host = host or FreeCADHost()
        self._bridge_factory = bridge_factory or WorkerBridge
        self._bridge = None
        self._panel = None
        self._dock = None
        self._command_registered = False

    @property
    def panel(self):
        """Return the docked panel, used by the CAM Job command."""
        return self._panel

    def _register_commands(self) -> None:
        """Register the namespaced Job command once when FreeCAD is available."""
        if self._command_registered or _FreeCADGui is None:
            return
        if not hasattr(_FreeCADGui, "addCommand"):
            return
        _FreeCADGui.addCommand(command_name(), SendJobCommand(lambda: self))
        self._command_registered = True

    def Initialize(self) -> None:
        """Create the bridge, panel, dock and command once."""
        if self._dock is not None:
            return
        self._bridge = self._bridge_factory()
        self._bridge.start()
        self._panel = CncControlPanel(
            self._bridge, job_source=post_process_selected_job
        )
        self._dock = QtWidgets.QDockWidget(translate("CncControl", "CNC Control"))
        self._dock.setWidget(self._panel)
        attach_dock(self._host, self._dock, "CncControlPanel")
        self._register_commands()
        if hasattr(self, "appendToolbar"):  # pragma: no cover - FreeCAD only
            self.appendToolbar("CNC", [command_name()])
            self.appendMenu("CNC", [command_name()])

    def Activated(self) -> None:
        """Show the panel when the workbench becomes active."""
        self.Initialize()
        self._dock.show()
        self._dock.raise_()

    def Deactivated(self) -> None:
        """Keep the panel and link alive when another workbench is selected."""

    def GetClassName(self) -> str:
        """Required FreeCAD Python-workbench class name."""
        return "Gui::PythonWorkbench"


def register_workbench() -> None:
    """Register one workbench instance with FreeCAD."""
    if _FreeCADGui is None:  # pragma: no cover - guarded by init_gui.py
        raise RuntimeError("FreeCADGui is not available")
    _FreeCADGui.addWorkbench(CncControlWorkbench())
