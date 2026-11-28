"""Explicit confirmation dialogs for sending a CAM job.

The panel takes a dialog provider so headless tests can replace Qt message
boxes with deterministic fakes. Safety decisions are never automatic.
"""

from freecad.cnc_control.freecad_adapter.host import translate
from freecad.cnc_control.freecad_adapter.qt import QtWidgets

_CONTEXT = "CncControl"


def _text(source: str) -> str:
    """Translate a user-facing string."""
    return translate(_CONTEXT, source)


class JobDialogs:
    """Qt implementation of the two required job decisions."""

    def confirm_job(self, result, parent=None) -> bool:
        """Ask for explicit confirmation before any pre-job check."""
        warnings = "\n".join(result.warnings) or _text("none")
        operations = ", ".join(result.operations) or _text("none")
        message = _text(
            "Send this CAM job?\n\nOperations: {operations}\n"
            "Lines: {lines}\nWarnings: {warnings}"
        ).format(
            operations=operations,
            lines=len(result.lines),
            warnings=warnings,
        )
        answer = QtWidgets.QMessageBox.question(
            parent,
            _text("Confirm CAM job"),
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def choose_check_mode(self, parent=None) -> bool | None:
        """Return True for check mode, False for a real run, None to cancel."""
        message = _text(
            "Preflight accepted. Run in GRBL check mode first?"
        )
        answer = QtWidgets.QMessageBox.question(
            parent,
            _text("Run mode"),
            message,
            QtWidgets.QMessageBox.Yes
            | QtWidgets.QMessageBox.No
            | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Yes,
        )
        if answer == QtWidgets.QMessageBox.Yes:
            return True
        if answer == QtWidgets.QMessageBox.No:
            return False
        return None
