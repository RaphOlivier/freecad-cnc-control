# Manual procedure 1 — E9 workbench and docked panel

Owner-only procedure. Run it in FreeCAD 1.1 stable or 1.2 dev. Do **not**
connect to a real machine: this step only checks that the workbench loads and
that the panel does not touch the serial link by itself.

1. Install the add-on from the Git repository with the FreeCAD Addon Manager
   (custom repository URL: `https://github.com/RaphOlivier/freecad-cnc-control`).
   Restart FreeCAD if the manager asks for it.
2. Select **CNC Control** in the workbench selector. Expected: the icon and
   menu text appear, and a dock widget named **CNC Control** opens on the
   right of the 3D view.
3. Check the panel contents: transport selector (Serial/Socket), endpoint and
   port/baud fields, Connect/Disconnect, link state, GRBL state, machine
   position, GRBL version, four real-time buttons, six jog buttons and an
   event log. No command is sent and no port is opened at this point.
4. Move the dock to another edge, close it, then switch to another workbench
   and back. Expected: no duplicate panel is created and the state label
   still reads `disconnected`.
5. Optional (virtual transport only): start a fake GRBL on a local TCP port,
   select **Socket**, enter `127.0.0.1` and that port, then press **Connect**.
   Expected: a `connected` event with `1.1h`, status polling updates the
   machine position, jog buttons append `Jog ...` lines to the log, and
   releasing a held jog button appends a jog-cancel real-time command.
6. Press **Disconnect**. Expected: state returns to `disconnected` and
   status polling stops.

Report to the agent: FreeCAD version, OS, any Python traceback in the Report
view, and whether each expected result matched. A software stop never
replaces a hardware emergency stop.
