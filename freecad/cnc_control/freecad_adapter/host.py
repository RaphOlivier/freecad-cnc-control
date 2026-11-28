"""Thin, injectable wrapper around the FreeCAD GUI host.

Only this module imports ``FreeCADGui``. The rest of the add-on receives a
host object with ``main_window()`` and ``add_dock_widget()`` methods, which
keeps GUI tests independent of a running FreeCAD instance.
"""

from freecad.cnc_control.freecad_adapter.qt import QtCore, QtWidgets


class FreeCADHost:
    """Real host: delegates dock creation to the FreeCAD main window."""

    def main_window(self):
        """Return FreeCAD's QMainWindow (import deferred for tests)."""
        import FreeCADGui  # type: ignore[import-not-found]

        return FreeCADGui.getMainWindow()

    def add_dock_widget(self, dock: QtWidgets.QDockWidget) -> None:
        """Add a dock widget to the right dock area and show it."""
        window = self.main_window()
        window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        dock.show()


def attach_dock(host, dock: QtWidgets.QDockWidget, object_name: str):
    """Create the dock once, or return the existing one with the same name."""
    dock.setObjectName(object_name)
    window = host.main_window()
    existing = window.findChild(QtWidgets.QDockWidget, object_name)
    if (
        existing is not None
        and window.dockWidgetArea(existing) != QtCore.Qt.NoDockWidgetArea
    ):
        return existing
    host.add_dock_widget(dock)
    return dock


def translate(context: str, text: str) -> str:
    """Mark a user-facing string for Qt translation."""
    return QtCore.QCoreApplication.translate(context, text)
