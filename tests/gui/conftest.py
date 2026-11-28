"""Shared Qt fixtures for headless GUI tests."""

import pytest

from freecad.cnc_control.freecad_adapter.qt import QtWidgets


@pytest.fixture(scope="session")
def qapp():
    """One QApplication for the whole GUI test session."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app
