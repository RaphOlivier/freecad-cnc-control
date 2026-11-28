"""Qt bridge tests with a fake worker and real QTimer event pumping."""

import time

from freecad.cnc_control.freecad_adapter.qt import QtWidgets
from freecad.cnc_control.gui.worker_bridge import WorkerBridge


class FakeWorker:
    """Minimal worker protocol with observable calls."""

    def __init__(self, emit) -> None:
        self.emit = emit
        self.submitted: list[dict] = []
        self.cancelled = False
        self.stopped = False

    def run(self) -> None:
        self.emit({"event": "ready"})

    def submit(self, command: dict) -> None:
        self.submitted.append(command)
        self.emit({"event": "accepted", "command": command.get("cmd")})

    def cancel(self) -> None:
        self.cancelled = True

    def stop(self) -> None:
        self.stopped = True
        self.emit({"event": "bye"})


def wait_until(predicate, timeout: float = 1.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        QtWidgets.QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_worker_events_are_emitted_on_the_gui_thread(qapp):
    instances: list[FakeWorker] = []

    def factory(emit):
        worker = FakeWorker(emit)
        instances.append(worker)
        return worker

    bridge = WorkerBridge(worker_factory=factory)
    received: list[dict] = []
    bridge.event_received.connect(received.append)
    try:
        bridge.start()
        assert wait_until(lambda: any(e.get("event") == "ready" for e in received))
        assert instances[0].emit is not None
    finally:
        bridge.stop()


def test_submit_starts_the_worker_when_needed(qapp):
    instances: list[FakeWorker] = []

    def factory(emit):
        worker = FakeWorker(emit)
        instances.append(worker)
        return worker

    bridge = WorkerBridge(worker_factory=factory)
    try:
        bridge.submit({"cmd": "status"})
        assert instances[0].submitted == [{"cmd": "status"}]
    finally:
        bridge.stop()


def test_realtime_uses_the_out_of_band_command(qapp):
    instances: list[FakeWorker] = []

    def factory(emit):
        worker = FakeWorker(emit)
        instances.append(worker)
        return worker

    bridge = WorkerBridge(worker_factory=factory)
    try:
        bridge.realtime("hold")
        assert instances[0].submitted == [
            {"cmd": "realtime", "params": {"command": "hold"}}
        ]
    finally:
        bridge.stop()


def test_stop_is_idempotent_and_emits_bye(qapp):
    instances: list[FakeWorker] = []

    def factory(emit):
        worker = FakeWorker(emit)
        instances.append(worker)
        return worker

    bridge = WorkerBridge(worker_factory=factory)
    received: list[dict] = []
    bridge.event_received.connect(received.append)
    bridge.start()
    assert wait_until(lambda: any(e.get("event") == "ready" for e in received))
    bridge.stop()
    assert wait_until(lambda: any(e.get("event") == "bye" for e in received))
    bridge.stop()
    assert len(instances) == 1
    assert instances[0].stopped is True
