# Decisions log

Confidence legend: [V] verified (source cited), [P] probable, [?] to check.

| ID | Decision | Confidence / source |
|---|---|---|
| E0-01 | Layout `freecad/cnc_control/` with subpackages core, worker, freecad_adapter, gui, testing, _vendor | [P] Addon Academy vendoring doc; to confirm for a workbench (H-07) |
| E0-02 | License LGPL-2.1-or-later, text downloaded from gnu.org | [V] https://www.gnu.org/licenses/lgpl-2.1.txt ; pending full license checks (FRAMING §7) |
| E0-03 | CI: GitHub Actions, 3 OS matrix, Python 3.12, pytest + ruff; GUI tests deferred to E9, integration to E3 | Decision (E0) |
| E0-04 | package.xml provisional; maintainer email uses GitHub noreply address | [P] format to verify against Addon Manager docs |
| E1-01 | Installed FreeCAD inspected: 1.1.4 (snap 2904, rev 44227+813), bundled Python 3.12.3, Qt 6.11.2, PySide6 6.11.2. PySide wheel availability for system Python 3.14 is irrelevant inside the snap. | [V] freecad.cmd inspection 2026-11-11 |
| E1-02 | Post-processor discovery: Path.Preferences.searchPathsPost() returns [defaultFilePath (empty by default), macro dir (/home/raph/snap/freecad/common/), Mod/CAM/Path/Post/scripts/, Mod/CAM/Path/Post/]; allAvailablePostProcessors() globs *_post.py in each. A third-party post must be named *_post.py and placed in one of these dirs (macro dir is the user-writable candidate). | [V] Mod/CAM/Path/Preferences.py lines 201-281 |
| E1-03 | Official grbl_post.py is LGPL-2.1-or-later: compatible with our license, can be studied and adapted. A refactored_grbl_post.py variant also exists. | [V] Mod/CAM/Path/Post/scripts/grbl_post.py header |
| E1-04 | Processor.py defines a _TempObject duck-typed class (Path/Name/InList/Label) used for fixtures: precedent for temporary non-document objects. Full 3D-view temp-object mechanism still to check at E11. | [V] Mod/CAM/Path/Post/Processor.py lines 58, 167-172 |
| E1-05 | Workbench layout confirmed by example: Mod/CAM has Init.py, InitGui.py, plus package dirs. Our workbench will follow the same pattern. | [V] Mod/CAM listing |
| E1-06 | Snap confinement: the snap cannot read /tmp (private per-snap tmp); inspection scripts must live in the home directory. | [V] tested 2026-11-11 |
| E3-01 | Fake GRBL (testing/fake_grbl.py): pure Python, official-doc behavior subset; injectable errors/alarms; ALARM delivered with next response (documented approximation of async push). Transports: core/transport.py with in-memory pair, TCP socket client, pty (POSIX only, echo and canonical mode disabled on the slave). Virtual transports only, never real ports. | [V] behavior per GRBL 1.1 docs; layout per AGENTS.md |
