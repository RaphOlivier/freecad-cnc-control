"""FreeCAD CAM adapter tests with fake Path objects (no FreeCAD needed)."""

import sys
import types
from types import SimpleNamespace

from freecad.cnc_control.freecad_adapter import cam as cam_adapter


class FakeCommand:
    def __init__(self, name, parameters=None) -> None:
        self.Name = name
        self.Parameters = parameters or {}


class FakePath:
    def __init__(self, commands) -> None:
        self.Commands = commands


class FakeOperation:
    def __init__(self, label, commands=None, group=None, active=True) -> None:
        self.Label = label
        self.Name = label
        self.Active = active
        self.Path = FakePath(commands or [])
        if group is not None:
            self.Group = group


class FakeJob:
    def __init__(self, operations) -> None:
        self.Operations = SimpleNamespace(Group=operations)


def install_fake_gui(monkeypatch, objects) -> None:
    gui = types.ModuleType("FreeCADGui")
    gui.Selection = SimpleNamespace(
        getSelectionEx=lambda: [SimpleNamespace(Object=obj) for obj in objects]
    )
    monkeypatch.setitem(sys.modules, "FreeCADGui", gui)


def test_post_process_selected_job_reads_active_operations(qapp, monkeypatch):
    job = FakeJob(
        [
            FakeOperation(
                "Pocket",
                [
                    FakeCommand("G0", {"X": 1.0}),
                    FakeCommand("G1", {"X": 2.0, "F": 100.0}),
                ],
            ),
            FakeOperation("Disabled", [FakeCommand("G1", {"X": 9.0})], active=False),
            FakeOperation(
                "Group",
                group=[
                    FakeOperation(
                        "Child", [FakeCommand("G1", {"Y": 3.0})]
                    )
                ],
            ),
        ]
    )
    install_fake_gui(monkeypatch, [object()])
    monkeypatch.setattr(cam_adapter, "_find_parent_job", lambda _obj: job)
    monkeypatch.setattr(cam_adapter, "_is_active", lambda op: op.Active)

    result = cam_adapter.post_process_selected_job()

    assert result is not None
    assert result.operations == ["Pocket", "Child"]
    assert result.lines[-4:] == ["G0X1", "G1X2F100", "(OP: Child)", "G1Y3"]
    assert all("Disabled" not in line for line in result.lines)


def test_no_selection_returns_none(qapp, monkeypatch):
    install_fake_gui(monkeypatch, [])

    assert cam_adapter.selected_job() is None
    assert cam_adapter.post_process_selected_job() is None


def test_job_without_active_commands_returns_none(qapp, monkeypatch):
    job = FakeJob([FakeOperation("Empty", active=False)])
    install_fake_gui(monkeypatch, [object()])
    monkeypatch.setattr(cam_adapter, "_find_parent_job", lambda _obj: job)
    monkeypatch.setattr(cam_adapter, "_is_active", lambda op: op.Active)

    assert cam_adapter.post_process_selected_job() is None
