"""Serve the pure-Python fake GRBL on a local TCP socket.

Virtual test tool only: it never opens a serial port and must not be used
with a real machine. Run it from the repository root, then connect the panel
with transport ``Socket`` and host/port ``127.0.0.1`` / ``23232``.
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

if __package__ in (None, ""):  # direct invocation from the repository root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freecad.cnc_control.testing.fake_grbl import FakeGrbl


def serve(host: str, port: int) -> None:
    """Accept local connections until interrupted with Ctrl+C."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    with server:
        server.bind((host, port))
        server.listen(1)
        actual_port = server.getsockname()[1]
        print(f"Fake GRBL listening on {host}:{actual_port} (Ctrl+C to stop)", flush=True)
        while True:
            conn, _ = server.accept()
            with conn:
                fake = FakeGrbl()
                conn.sendall(fake.banner)
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    out = fake.process(data)
                    if out:
                        conn.sendall(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=23232)
    args = parser.parse_args()
    try:
        serve(args.host, args.port)
    except KeyboardInterrupt:
        print("Fake GRBL stopped", flush=True)


if __name__ == "__main__":
    main()
