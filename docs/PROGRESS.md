STATUS: RUNNING
STATUS: NOT_STARTED

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
