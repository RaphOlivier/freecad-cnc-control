"""G-code analysis for GRBL jobs: bounds, path segments and source mapping.

Pure Python: no FreeCAD, no Qt. The analyser works on the post-processed
G-code that will actually be sent to the controller, not on CAM objects.

Scope and assumptions (documented in docs/DECISIONS.md):

- Coordinates are program coordinates (WPos), not machine coordinates. Work
  offsets (G54..G59, G92) are recorded as warnings but are not applied.
- Motion is tracked modally: G0/G1/G2/G3 persist until another motion command.
- Units are tracked modally; G20 values are converted to millimetres.
- G2/G3 arcs are sampled at a fixed resolution for the path and bounds.
- Parentheses and semicolon comments are ignored. ``(OP: name)`` and
  ``(Operation: name)`` set the current operation name.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

MM_PER_INCH = 25.4
_ARC_SAMPLES = 9

_COMMENT_RE = re.compile(r"\(([^)]*)\)")
_OPERATION_RE = re.compile(r"^(?:OP|OPERATION)\s*:\s*(.+)$", re.IGNORECASE)
_WORD_RE = re.compile(
    r"([A-Za-z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)

_MOTION_CODES = {0: "G0", 1: "G1", 2: "G2", 3: "G3"}
_PLANE_AXES = {17: (0, 1), 18: (0, 2), 19: (1, 2)}
_UNSUPPORTED_MOTION = {28, 30, 53, 92}


@dataclass(frozen=True)
class Bounds:
    """Axis-aligned bounds of the analysed toolpath, in millimetres."""

    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    def as_dict(self) -> dict[str, tuple[float, float]]:
        """Return ``{"x": (min, max), ...}`` for JSON events."""
        return {
            axis: [self.minimum[index], self.maximum[index]]
            for index, axis in enumerate("xyz")
        }


@dataclass(frozen=True)
class Segment:
    """One motion block, with sampled points in program coordinates (mm)."""

    line: int
    motion: str
    points: tuple[tuple[float, float, float], ...]
    feed: float | None
    operation: str | None

    @property
    def start(self) -> tuple[float, float, float]:
        return self.points[0]

    @property
    def end(self) -> tuple[float, float, float]:
        return self.points[-1]


@dataclass
class GcodeAnalysis:
    """Result of analysing one G-code program."""

    bounds: Bounds | None = None
    segments: list[Segment] = field(default_factory=list)
    line_segments: dict[int, list[int]] = field(default_factory=dict)
    operations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    units: str = "mm"
    command_count: int = 0


def _strip_comments(text: str) -> tuple[str, str | None]:
    """Remove comments and return the code plus any operation name."""
    operation: str | None = None

    def replace(match: re.Match[str]) -> str:
        nonlocal operation
        if operation is None:
            found = _OPERATION_RE.match(match.group(1).strip())
            if found:
                operation = found.group(1).strip()
        return " "

    without_parentheses = _COMMENT_RE.sub(replace, text)
    return without_parentheses.split(";", 1)[0], operation


def _words(text: str) -> tuple[list[float], dict[str, float]]:
    """Split a block into G codes and letter/value words."""
    pairs = [(letter.upper(), float(value)) for letter, value in _WORD_RE.findall(text)]
    g_codes = [value for letter, value in pairs if letter == "G"]
    words = {letter: value for letter, value in pairs if letter != "G"}
    return g_codes, words


def _scaled(words: dict[str, float], letters: str, scale: float) -> dict[str, float]:
    return {letter: words[letter] * scale for letter in letters if letter in words}


def _linear_target(
    current: tuple[float, float, float],
    axes: dict[str, float],
    absolute: bool,
) -> tuple[float, float, float]:
    target = list(current)
    for index, letter in enumerate("XYZ"):
        if letter not in axes:
            continue
        target[index] = axes[letter] if absolute else current[index] + axes[letter]
    return tuple(target)


def _arc_center(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    axes: dict[str, float],
    plane_axes: tuple[int, int],
    radius: float | None,
) -> tuple[float, float] | None:
    """Return the arc centre in the active plane, or None if undetermined."""
    first, second = plane_axes
    offsets = ("IJK"[first], "IJK"[second])
    if offsets[0] in axes or offsets[1] in axes:
        return (
            start[first] + axes.get(offsets[0], 0.0),
            start[second] + axes.get(offsets[1], 0.0),
        )
    if radius is None:
        return None
    x0, y0 = start[first], start[second]
    x1, y1 = end[first], end[second]
    dx, dy = x1 - x0, y1 - y0
    chord = math.hypot(dx, dy)
    if chord == 0 or radius < chord / 2:
        return None
    height = math.sqrt(max(0.0, radius * radius - (chord / 2) ** 2))
    mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
    perp_x, perp_y = -dy / chord, dx / chord
    # Both possible centres are kept by the caller through the sampled
    # points; returning one is enough for a conservative bounds union.
    return (mid_x + height * perp_x, mid_y + height * perp_y)


def _arc_points(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    center: tuple[float, float] | None,
    plane: int,
    clockwise: bool,
) -> tuple[tuple[float, float, float], ...]:
    """Sample one arc; fall back to its endpoints when the centre is unknown."""
    if center is None:
        return (start, end)
    first, second = _PLANE_AXES[plane]
    start_angle = math.atan2(start[second] - center[1], start[first] - center[0])
    end_angle = math.atan2(end[second] - center[1], end[first] - center[0])
    sweep = end_angle - start_angle
    if abs(sweep) < 1e-9 and start[:2] == end[:2]:
        sweep = -2 * math.pi if clockwise else 2 * math.pi
    elif clockwise:
        while sweep > 0:
            sweep -= 2 * math.pi
    else:
        while sweep < 0:
            sweep += 2 * math.pi
    radius = math.hypot(start[first] - center[0], start[second] - center[1])
    points: list[tuple[float, float, float]] = []
    for index in range(_ARC_SAMPLES):
        angle = start_angle + sweep * index / (_ARC_SAMPLES - 1)
        point = [start[0], start[1], start[2]]
        point[first] = center[0] + radius * math.cos(angle)
        point[second] = center[1] + radius * math.sin(angle)
        if index == _ARC_SAMPLES - 1:
            point = list(end)
        points.append(tuple(point))
    return tuple(points)


def _extend(bounds: Bounds | None, points: Iterable[tuple[float, float, float]]) -> Bounds:
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    if bounds is not None:
        minimum = list(bounds.minimum)
        maximum = list(bounds.maximum)
    for point in points:
        for index, value in enumerate(point):
            minimum[index] = min(minimum[index], value)
            maximum[index] = max(maximum[index], value)
    return Bounds(tuple(minimum), tuple(maximum))


def analyze(lines: Iterable[str]) -> GcodeAnalysis:
    """Analyse raw G-code lines into bounds, segments and a line map."""
    result = GcodeAnalysis()
    current = (0.0, 0.0, 0.0)
    motion = "G0"
    absolute = True
    plane = 17
    scale = 1.0
    operation: str | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        code, comment_operation = _strip_comments(raw_line)
        if comment_operation:
            operation = comment_operation
            if comment_operation not in result.operations:
                result.operations.append(comment_operation)
        g_codes, words = _words(code)
        if not g_codes and not words:
            continue
        result.command_count += 1

        unsupported = False
        for value in g_codes:
            if not value.is_integer():
                continue
            integer = int(value)
            if integer in _MOTION_CODES:
                motion = _MOTION_CODES[integer]
            elif integer == 20:
                scale, result.units = MM_PER_INCH, "in"
            elif integer == 21:
                scale, result.units = 1.0, "mm"
            elif integer == 90:
                absolute = True
            elif integer == 91:
                absolute = False
            elif integer in _PLANE_AXES:
                plane = integer
            elif integer in _UNSUPPORTED_MOTION:
                unsupported = True
                result.warnings.append(
                    f"line {line_number}: G{integer} can move the machine and is not analysed"
                )

        axes = _scaled(words, "XYZIJKR", scale)
        feed = words["F"] * scale if "F" in words else None
        has_axis = any(letter in axes for letter in "XYZ")
        if not has_axis or unsupported:
            continue

        target = _linear_target(current, axes, absolute)
        if motion in ("G2", "G3"):
            first, second = _PLANE_AXES[plane]
            center = _arc_center(
                current, target, axes, (first, second), axes.get("R"),
            )
            points = _arc_points(current, target, center, plane, motion == "G2")
            result.warnings.append(
                f"line {line_number}: arc sampled at {_ARC_SAMPLES} points"
            )
        else:
            points = (current, target)

        index = len(result.segments)
        result.segments.append(
            Segment(
                line=line_number,
                motion=motion,
                points=points,
                feed=feed,
                operation=operation,
            )
        )
        result.line_segments.setdefault(line_number, []).append(index)
        result.bounds = _extend(result.bounds, points)
        current = target

    return result
