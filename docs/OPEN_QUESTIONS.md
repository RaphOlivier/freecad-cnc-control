# Open questions

- Confirm the namespace/package layout expected by the Addon Manager for a workbench (H-07, E0-01).
- Confirm package.xml schema details against the Addon Manager documentation before E16.
- Final maintainer email for package.xml (placeholder: GitHub noreply).
- PySide wheels availability for Python 3.14 on the owner machine (needed at E9).
- Plan drift (2026-11-28): LAUNCH_PROMPT E7 = G-code analysis, E8 = pre-job checks; the merged E7/E8 commits delivered serial robustness, dev dependencies and connection state instead. Do we implement the missing G-code analysis and pre-job safety checks before E9, or accept the current core as the end of E8 and start the FreeCAD layer now? Owner decision needed because the missing checks are safety-critical. Resolved 2026-11-28: owner chose to implement the missing E7/E8 scope before E9.
- Safety review (2026-11-28): independent review found bypassable preflight, injected `$C`, under-reported arc bounds and ignored WCO. Owner chose to fix before E9. Resolved 2026-11-28 by commits `0427b7d`, `1fa4485` and the current worker hardening; all findings have regression tests.
