STATUS: RUNNING

# Progress log

- 2026-11-09: framing interview done (16 waves), deliverables written (docs/FRAMING.md, AGENTS.md, docs/LAUNCH_PROMPT.md).
- 2026-11-09: public GitHub repository created (README only). Owner machine: Kubuntu, git, gh, Python 3.14 installed.
- 2026-11-10: handoff package for the orchestrator written (docs/handoff/). No code written yet.

## Next
E0 in docs/LAUNCH_PROMPT.md (repository skeleton, CI on 3 systems).
- 2026-11-11: handoff package merged into main (commit 6bf35dd, by the owner).
- 2026-11-11: E0 done: repository skeleton, CI on 3 systems (core+worker+style), LGPL-2.1-or-later LICENSE, provisional package.xml, placeholder test.

## Next
E1: inspect installed FreeCAD API (read-only, freecadcmd); record findings in docs/DECISIONS.md.
- 2026-11-11: E1 done: installed FreeCAD 1.1.4 (snap) inspected read-only; post-processor discovery mechanism, official GRBL post license, _TempObject precedent and workbench layout recorded in docs/DECISIONS.md (E1-01..E1-06).

## Next
E2: GRBL 1.1 protocol parsing in core/ (ok, errors, alarms, status reports), from the GRBL 1.1 documentation.
- 2026-11-11: E2 done: GRBL 1.1 protocol parser in core/grbl_protocol.py (18 tests, ruff clean), merged with green CI.
- 2026-11-11: dev container added (.devcontainer/) so the project can be developed in GitHub Codespaces from a browser, with no local machine. Matches CI (Python 3.12, pytest, ruff); build-essential and socat included for the future compiled-GRBL integration tests (E3). Optional script .devcontainer/install-freecad-appimage.sh for read-only FreeCAD inspection (snap is not available inside containers; AppImage fallback per docs/FRAMING.md).

## Next
E3-E8: core communication testable without FreeCAD (see docs/LAUNCH_PROMPT.md); checkpoints after E6 and E8.
- 2026-11-11: git policy change (owner decision): direct pushes to `main` are allowed; the "the owner merges" rule was removed from AGENTS.md (sections 8.7 and 8.8). Force-push remains forbidden.
- 2026-11-11: E3 done: fake GRBL emulator plus in-memory, socket and pty transports; 27 tests green (see docs/FAILURES.md for the pty line-discipline incident).

## Next
E4: character-counting streamer with prioritized real-time commands.
- 2026-11-11: E4 done: CharacterCountingStreamer (core/streamer.py) with character counting, push/ack separation, error stop+drain, alarm abort, unsendable-line detection; 10 tests against the fake GRBL (see docs/FAILURES.md).

## Next
E5: connection manager (connect/disconnect, welcome handshake, status polling) on top of transports + streamer.
- 2026-11-11: E5 done: GrblConnection (handshake, send_line, poll_status, streaming, close); 9 tests.

## Next
E6: worker process owning the transport (thread), JSON command/event protocol toward the GUI, pyserial serial transport (real hardware path, still behind the fake for tests).
- 2026-11-18: E6 done: Worker thread + JSON command/event protocol (connect, send, status, stream, disconnect, shutdown); 10 tests, 55 total.

## Next
E7: real serial transport (pyserial behind the fake), stream cancellation; then passation review point.
- 2026-11-19: E7 done: read timeouts (connect/send/status), out-of-band stream cancellation, SerialTransport (pyserial, loop:// testable); worker rewritten whole after partial-patch incident (see docs/FAILURES.md).

## Next
E8: end of the communication core; then passation checkpoint #2 before the FreeCAD part (E9+).
- 2026-11-23: E7 final round: bounded reads, pytest-timeout in CI, fake-serve race fixed (stop_fake joined before silent-link scenarios). 62 tests green locally.

## Next
- 2026-11-28: development resumed from a fresh clone on the owner's machine. `main` is at 899de7f (E8.2 merged). 68 test functions are defined; CI on that commit is green on Linux and Windows, while the macOS job was cancelled by runner capacity (no test failure). The local Python has no pytest or pip, so tests could not be rerun locally.
- 2026-11-28: plan drift identified. `docs/LAUNCH_PROMPT.md` assigns E7 to G-code analysis and E8 to pre-job checks, but the merged E7/E8 work delivered serial robustness, dev dependencies and explicit connection state. G-code parsing, machine-limit checks, explicit confirmation and GRBL check mode are still absent. This is safety-critical scope: owner decision requested in `docs/OPEN_QUESTIONS.md` before writing code.
- 2026-11-28: GitHub MCP connected from the project with a fine-grained PAT stored outside the repo; local `opencode.json` added and documented as TOOL-01. Local pytest is unavailable (`No module named pytest`); CI remains the test gate.
- 2026-11-28: local commits `e9a851a` and `dd956ab` pushed to `origin/main` (fast-forward, no force). Git uses a local credential helper that reads the PAT file without storing the token in configuration (TOOL-02).
- 2026-11-28: owner confirmed the plan-drift option: fill the missing E7/E8 scope before E9. E7 (G-code analysis) added in `core/gcode.py` with 6 tests; 73 passed, 1 skipped locally, ruff clean.
