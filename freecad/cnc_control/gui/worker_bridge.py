"""Qt bridge between the GUI thread and the worker thread.

The worker owns the transport; Qt objects live only in the GUI thread. Events
are queued by the worker and re-emitted by a QTimer running on the GUI thread,
so no Qt method is ever called from the worker thread.
"""

import queue
import threading

from freecad.cnc_control.core.worker import Worker
from freecad.cnc_control.freecad_adapter.qt import QtCore


class WorkerBridge(QtCore.QObject):
    """Starts a Worker and forwards its events as a Qt signal."""

    event_received = QtCore.Signal(dict)

    def __init__(self, worker_factory=None, parent=None) -> None:
        super().__init__(parent)
        self._worker_factory = worker_factory or Worker
        self._events: queue.Queue[dict] = queue.Queue()
        self._worker: Worker | None = None
        self._thread: threading.Thread | None = None
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._drain)
        self._timer.start(20)

    def start(self) -> None:
        """Start the worker thread once."""
        if self._worker is not None:
            return
        self._worker = self._worker_factory(emit=self._events.put)
        self._thread = threading.Thread(target=self._worker.run, daemon=True)
        self._thread.start()

    def submit(self, command: dict) -> None:
        """Queue a normal worker command."""
        if self._worker is None:
            self.start()
        self._worker.submit(command)

    def realtime(self, command: str) -> None:
        """Send a real-time byte without queuing it behind G-code lines."""
        self.submit({"cmd": "realtime", "params": {"command": command}})

    def cancel(self) -> None:
        """Cancel the current stream out-of-band."""
        if self._worker is not None:
            self._worker.cancel()

    def stop(self) -> None:
        """Stop the worker thread and the event pump."""
        if self._worker is not None:
            self._worker.stop()
            if self._thread is not None:
                self._thread.join(timeout=2.0)
            self._drain()
            self._worker = None
            self._thread = None
        self._timer.stop()

    def _drain(self) -> None:
        """Emit queued events from the GUI thread."""
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                return
            self.event_received.emit(event)
