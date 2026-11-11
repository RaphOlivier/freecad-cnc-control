# Decisions log

Confidence legend: [V] verified (source cited), [P] probable, [?] to check.

| ID | Decision | Confidence / source |
|---|---|---|
| E0-01 | Layout `freecad/cnc_control/` with subpackages core, worker, freecad_adapter, gui, testing, _vendor | [P] Addon Academy vendoring doc; to confirm for a workbench (H-07) |
| E0-02 | License LGPL-2.1-or-later, text downloaded from gnu.org | [V] https://www.gnu.org/licenses/lgpl-2.1.txt ; pending full license checks (FRAMING §7) |
| E0-03 | CI: GitHub Actions, 3 OS matrix, Python 3.12, pytest + ruff; GUI tests deferred to E9, integration to E3 | Decision (E0) |
| E0-04 | package.xml provisional; maintainer email uses GitHub noreply address | [P] format to verify against Addon Manager docs |
