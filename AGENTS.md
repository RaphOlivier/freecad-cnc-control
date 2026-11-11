
# AGENTS.md

Project: FreeCAD add-on "CNC Control" (provisional name) to drive CNC machines from FreeCAD.
This file is read by coding agents (Mistral Vibe reads AGENTS.md; Claude Code reads CLAUDE.md, which points here).
Orchestration context (owner, other projects, status, research): see `docs/handoff/README.md`.

The conversation with the owner is in French. Code, comments, commit messages and repository documentation are in English (exception: the handoff documents in `docs/handoff/` and `docs/FRAMING.md` are in French). UI strings are translatable (English source).

## 1. Goals and non-goals

Milestone 1 (single milestone, delivered at once): GRBL 1.1 over serial, in a dedicated FreeCAD workbench with a docked panel.
- connect/disconnect, status and position, real-time commands (hold, resume, soft reset)
- jog: fixed steps and continuous (stops on key release or focus loss)
- streaming of G-code (character-counting), alarms and errors handled without auto-resume
- $H, $X, read-only $$, work offsets (G54..G59 and G92), zeroing
- feed overrides, macros (lists of G-code lines in an add-on file), probing (Z, then X/Y edges)
- G-code source: any file, or the selected CAM Job through our own GRBL post-processor
- 3D marker + progress of machined path as temporary view objects, computed from the G-code
- pre-job checks (limits from $$, explicit confirmation, GRBL check mode then real run), pause on link loss
- optional serial exchange log (rotating files)

Success: a complete job runs end to end against the emulator with an automated test.
If time runs short, drop in this order: probing, macros, feed overrides.

Non-goals for milestone 1: other controllers, LinuxCNC, kinematics, RS-232 autodetection, other machine types, GRBL 0.9/grblHAL, 4th axis, publication in the official Addon Manager catalog.
Long-term vision (keep the architecture open, do not build it now): mills, lathes, embroidery, laser, plasma; GRBL/grblHAL, FluidNC, Smoothieware, Marlin, g2core, LinuxCNC, Duet, Klipper; machine configuration and kinematics; RS-232 parameter discovery; LinuxCNC mode as an Axis replacement.

## 2. Architecture principles

1. Do not modify FreeCAD core. Reuse FreeCAD's CAM workbench, post-processors, and later machine files/tool libraries.
2. Strict layering, only the adapter imports FreeCAD:
   - `core/`: pure Python, no FreeCAD, no Qt. GRBL protocol parsing, streamer, G-code parsing (bounds, path, line-to-segment map), controller interface, transports.
   - `worker/`: separate OS process that owns the serial link. Talks to the GUI via line-delimited JSON over standard streams. Heartbeat from the GUI (default every 500 ms); if lost for 2 s the worker sends a feed hold. Real-time commands bypass the streaming queue.
   - `freecad_adapter/`: the only package importing FreeCAD. Isolates differences between FreeCAD 1.1 and 1.2 dev.
   - `gui/`: Qt panel and workbench, no GRBL assumptions; asks the controller interface for capabilities.
   - `testing/`: fake GRBL emulator (pure Python) and transports (in-memory, socket, pty on Linux/macOS).
3. Controller interface (one implementation now, GRBL): connect, disconnect, send line, stream, real-time commands, state, jog, capabilities. No GRBL-specific logic in the GUI.
4. No premature generalization: no kinematics, no LinuxCNC code in milestone 1.
5. Machine configuration: small JSON file owned by the add-on, designed to be alignable later with FreeCAD `.fcm` machine files.
6. Light dependencies. pyserial is vendored under `_vendor/` with its license text. Ask the owner before adding anything else.

## 3. Repository layout (proposed)

```
freecad/cnc_control/{core,worker,freecad_adapter,gui,testing,_vendor}/
package.xml              # Addon Manager metadata
tests/{core,worker,gui,integration}/
docs/{FRAMING.md,PROGRESS.md,DECISIONS.md,OPEN_QUESTIONS.md,manual-tests/,handoff/}
REPORT.md                # final report
AGENTS.md                # this file (CLAUDE.md points here)
LICENSE                  # LGPL-2.1-or-later (pending license checks)
```
Verify the namespace/package layout expected by FreeCAD's Addon Manager before fixing it.

## 4. FreeCAD integration rules

- Never guess FreeCAD API names, modules, paths or signatures. Check the installed FreeCAD code (read-only inspection with the FreeCAD command-line binary is allowed) and record each finding in `docs/DECISIONS.md` as verified, probable or to-check, with the source.
- Target FreeCAD 1.1 stable and 1.2 dev. FreeCAD moves fast (Path became CAM in 1.0; tool library rework in 1.1). Isolate all version differences in `freecad_adapter/`.
- FreeCAD CAM stores toolpaths in an internal G-code form; post-processors convert it to the machine dialect. Our preview and progress are computed from the post-processed G-code, not from CAM objects.
- Our own GRBL post-processor must emit operation-name comments. Verify how FreeCAD discovers third-party post-processors before writing it.
- Marker and path overlays are temporary objects, never saved in the user's document. Verify the mechanism first.
- Python dependencies cannot rely on the Addon Manager (pyserial is not on its allow list as far as known); keep vendoring.

## 5. Safety rules (non-negotiable)

- Never connect to a real machine on your own initiative. Tests and agent tooling use virtual transports only (in-memory, socket, pty, emulator). Any test on hardware is a manual procedure written in `docs/manual-tests/` and run by the owner.
- No movement without an explicit user action. No automatic homing or movement on connect.
- Stop must stay reachable even if the GUI freezes: the worker process owns the link and applies a feed hold on heartbeat loss.
- Real-time commands (hold, resume, reset, jog cancel, overrides) never wait in the streaming queue.
- Alarms: stop streaming, display, no resume without explicit action. Link loss: automatic pause; resume only after reconnection and explicit confirmation.
- Before a real job: refuse if the G-code exceeds machine limits read from `$$`; ask explicit confirmation; offer GRBL check mode first.
- Macros containing motion and probing cycles require explicit confirmation each time.
- Document in user docs that a software stop never replaces a hardware emergency stop.

## 6. Conventions

- Python 3, type hints, small functions, docstrings in English. Code style checker and formatter configured in CI.
- Commits: English, imperative, one small tested step each. Never commit with failing tests.
- UI strings go through Qt translation functions; no hard-coded user-facing text outside them.
- Licensing: project is LGPL-2.1-or-later (pending checks). Do not copy code from GPL projects (bCNC GPLv2, GRBL/Candle/GRBL-Plotter GPLv3). Study ideas only. Any third-party code, even permissive, needs the owner's approval and a notice.

## 7. Test commands

Core and worker (no FreeCAD needed, Linux/Windows/macOS):
```
pytest tests/core tests/worker
```
Qt tests, headless (PySide installed separately in the test environment, version aligned with FreeCAD; check that PySide wheels exist for the Python version in use):
```
QT_QPA_PLATFORM=offscreen pytest tests/gui
```
Integration against a compiled GRBL simulator (Linux only; pseudo-terminal via socat):
```
pytest -m integration tests/integration
```
Continuous integration runs on GitHub Actions on the three systems for core/worker/gui; integration only on Linux. There is no automated test against a real FreeCAD; the owner runs the manual procedures in `docs/manual-tests/` at key steps.

## 8. How the agent works

1. Small steps, each with its test. Write the test first when it is practical. Run the relevant tests before every commit.
2. Verify API facts in the installed code instead of guessing. Record the result.
3. Keep documentation current at every commit: `docs/PROGRESS.md` (done, in progress, next), `docs/DECISIONS.md` (decisions and assumptions with confidence), `docs/OPEN_QUESTIONS.md`.
4. Decide alone: internal design choices, naming, structure, test design, documented assumptions.
5. Ask the owner first for: a new dependency, a license decision, a major architecture change, anything touching machine safety, publication, destructive git operations, third-party code reuse.
6. Stop after 3 failed attempts on the same step, or at usage limit. Write the state in `docs/PROGRESS.md` so another agent can resume without asking anything essential.
7. Git: work on a dedicated branch (for example `agent/milestone-1`), one commit per small tested step, push only that branch, never force-push, never touch `main`. The owner merges.
8. Commands to refuse or to submit to the owner before running: `git push` to `main`, `--force`, `rm -rf`, `sudo`, `curl | sh`, any access to `/dev/tty*`, `/dev/cu.*` or `COM*` ports, installation of packages not yet approved.
9. At the end of milestone 1: write `REPORT.md` (done, tested, open points, manual procedures to run, risks) and a short summary in chat. Then continue on the next milestone (RS-232 parameter discovery) under the same safety rules (virtual ports only; real-device trials remain manual procedures run by the owner), unless the owner or the orchestrator says otherwise.

## 9. Roadmap after milestone 1 (order set by the owner, details left to the agent)

1. RS-232 link with parameter discovery (safe, no motion, only harmless commands, owner confirmation; tests on virtual ports only)
2. Other controllers (FluidNC, Smoothieware, ...)
3. Machine configuration and kinematics
4. LinuxCNC mode (Axis replacement; study the `linuxcnc` Python module, HAL, INI files)
First extra machine type: laser cutter.

## 10. Status line (for scripts and for relays between agents)

At the end of every session, set the first line of `docs/PROGRESS.md` to exactly one of:
STATUS: RUNNING
STATUS: BLOCKED       (3 failed attempts, or the owner's approval is needed)
STATUS: NEEDS_OWNER   (a manual procedure must be run by the owner)
STATUS: DONE

