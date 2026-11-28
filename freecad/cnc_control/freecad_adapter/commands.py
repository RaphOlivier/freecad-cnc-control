"""FreeCAD GUI commands for the CNC Control workbench."""

from pathlib import Path

from freecad.cnc_control.freecad_adapter.host import translate

_ICON = Path(__file__).resolve().parents[1] / "resources" / "icons" / "CNCControl.svg"
_COMMAND_NAME = "CNCControl_SendJob"


class SendJobCommand:
    """Act on the Job selected in FreeCAD through the workbench panel."""

    def __init__(self, workbench_provider) -> None:
        self._workbench_provider = workbench_provider

    def GetResources(self) -> dict[str, str]:
        """Return the menu text, tooltip and icon expected by FreeCAD."""
        return {
            "MenuText": translate("CncControl", "Send selected CAM Job"),
            "ToolTip": translate(
                "CncControl", "Post-process the selected CAM Job and send it to GRBL"
            ),
            "Pixmap": str(_ICON),
        }

    def IsActive(self) -> bool:
        """The command is always available; the panel validates the selection."""
        return True

    def Activated(self) -> None:
        """Delegate to the panel; no machine action happens here."""
        workbench = self._workbench_provider()
        panel = getattr(workbench, "panel", None)
        if panel is not None:
            panel.send_job()


def command_name() -> str:
    """Return the namespaced FreeCAD command name."""
    return _COMMAND_NAME
