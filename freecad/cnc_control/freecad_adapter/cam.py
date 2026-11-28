"""Read a selected FreeCAD CAM Job and convert it to GRBL lines.

Only this module imports FreeCAD modules. The command conversion itself lives
in :mod:`core.cam_post`, which stays free of FreeCAD and Qt. Verified against
FreeCAD 1.1.4: ``job.Operations.Group``, ``PathUtil.activeForOp``,
``obj.Path.Commands``, ``Command.Name`` and ``Command.Parameters``.
"""

from freecad.cnc_control.core.cam_post import (
    CamCommand,
    CamOperation,
    PostResult,
    post_process,
)


def _find_parent_job(obj):
    """Resolve the Job that owns a selected CAM object (FreeCAD API)."""
    import PathUtils  # type: ignore[import-not-found]

    return PathUtils.findParentJob(obj)


def _is_active(op) -> bool:
    """True when the operation is enabled (FreeCAD API)."""
    import Path.Base.Util as PathUtil  # type: ignore[import-not-found]

    return bool(PathUtil.activeForOp(op))


def selected_job():
    """Return the single selected CAM Job, or None."""
    import FreeCADGui  # type: ignore[import-not-found]

    selection = FreeCADGui.Selection.getSelectionEx()
    if len(selection) != 1:
        return None
    return _find_parent_job(selection[0].Object)


def _iter_operations(obj):
    """Yield one ``CamOperation`` per active Path feature below ``obj``."""
    if hasattr(obj, "Group"):
        for child in obj.Group:
            if _is_active(child):
                yield from _iter_operations(child)
        return
    if not hasattr(obj, "Path"):
        return
    commands = [
        CamCommand(str(command.Name), dict(command.Parameters))
        for command in obj.Path.Commands
    ]
    if not commands:
        return
    label = getattr(obj, "Label", None) or getattr(obj, "Name", "Operation")
    yield CamOperation(str(label), commands)


def post_process_selected_job() -> PostResult | None:
    """Post-process the active operations of the selected Job."""
    job = selected_job()
    if job is None or not hasattr(job, "Operations"):
        return None
    operations: list[CamOperation] = []
    for obj in job.Operations.Group:
        if not _is_active(obj):
            continue
        operations.extend(_iter_operations(obj))
    if not operations:
        return None
    return post_process(operations)
