"""Qt compatibility imports for the FreeCAD adapter and GUI packages.

FreeCAD 1.x re-exports PySide6 under the ``PySide`` module; outside FreeCAD
(tests, CI) we fall back to PySide6 then PySide2. GUI code imports Qt from
here so version differences stay inside the adapter (AGENTS.md §2).
"""

try:  # pragma: no cover - exercised inside FreeCAD
    from PySide import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - depends on the host interpreter
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtGui, QtWidgets

__all__ = ["QtCore", "QtGui", "QtWidgets"]
