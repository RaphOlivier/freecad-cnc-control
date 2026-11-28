"""G-code analysis for GRBL jobs: bounds, path segments and source mapping.

Pure Python: no FreeCAD, no Qt. The analyser works on the post-processed
G-code that will actually be sent to the controller, not on CAM objects.

Scope and assumptions (documented in docs/DECISIONS.md):

- Coordinates are program coordinates (WPos); work offsets are applied later,
  by core/preflight.py, from the controller status report.
- Motion is tracked modally: G0/G1/G2/G3 persist until another motion command.
- Units are tracked modally; G20 values are converted to millimetres.
- G2/G3 arcs are sampled at a fixed resolution for the path, while bounds use
  the exact extrema of the arc (including helical off-plane interpolation).
- Commands that can move the machine outside the analysed motion model
  (G10, G28, G30, G38.x, G43.x, G53, G92.x) are refused by preflight.
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
_TWO_PI = 2 * math.pi
_EPS = 1e-9

_COMMENT_RE = re.compile(r"\(([^)]*)\)")
_OPERATION_RE = re.compile(r"^(?:OP|OPERATION)\s*:\s*(.+)$", re.IGNORECASE)
_WORD_RE = re.compile(
    r"([A-Za-z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
)

_MOTION_CODES = {0: "G0", 1: "G1", 2: "G2", 3: "G3"}
_PLANE_AXES = {17: (0, 1), 18: (0, 2), 19: (1, 2)}
_UNSUPPORTED_G = {10, 28, 30, 43, 53, 92}  # offsets, homing moves, probing setup


@dataclass(frozen=True)
class Bounds:
    """Axis-aligned bounds of the analysed toolpath, in millimetres."""

    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    def as_dict(self) -> dict[str, list[float]]:
        """Return ``{"x": [min, max], ...}`` for JSON events."""
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
    unsupported_motion: bool = False
    units: str = "mm"
    command_count: int = 0


@dataclass(frozen=True)
class _ArcGeometry:
    """Resolved centre and sweep of one arc, in the active plane."""

    center: tuple[float, float]
    radius: float
    start_angle: float
    sweep: float  # radians, negative for G2 (clockwise)


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


def _is_unsupported_g(value: float) -> bool:
    """True for commands that can change machine state outside our model."""
    integer = math.floor(value)
    return integer in _UNSUPPORTED_G or integer == 38  # G38.x probing cycles


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


def _sweep(start_angle: float, end_angle: float, clockwise: bool, full: bool) -> float:
    """Signed sweep in the requested direction, in (-2pi, 0] or [0, 2pi)."""
    if full:
        return -_TWO_PI if clockwise else _TWO_PI
    raw = end_angle - start_angle
    sweep = raw % (-_TWO_PI) if clockwise else raw % _TWO_PI
    if abs(sweep) < _EPS:
        sweep = -_TWO_PI if clockwise else _TWO_PI
    return sweep


def _geometry_for_center(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    center: tuple[float, float],
    plane: int,
    clockwise: bool,
) -> _ArcGeometry | None:
    first, second = _PLANE_AXES[plane]
    radius = math.hypot(start[first] - center[0], start[second] - center[1])
    if radius < _EPS:
        return None
    full = (
        abs(start[first] - end[first]) < _EPS
        and abs(start[second] - end[second]) < _EPS
    )
    start_angle = math.atan2(start[second] - center[1], start[first] - center[0])
    end_angle = math.atan2(end[second] - center[1], end[first] - center[0])
    return _ArcGeometry(
        center,
        radius,
        start_angle,
        _sweep(start_angle, end_angle, clockwise, full),
    )


def _arc_geometry(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    axes: dict[str, float],
    plane: int,
    clockwise: bool,
) -> _ArcGeometry | None:
    """Resolve the arc centre from IJK offsets or from an R word."""
    first, second = _PLANE_AXES[plane]
    offset_letters = ("IJK"[first], "IJK"[second])
    if offset_letters[0] in axes or offset_letters[1] in axes:
        center = (
            start[first] + axes.get(offset_letters[0], 0.0),
            start[second] + axes.get(offset_letters[1], 0.0),
        )
        return _geometry_for_center(start, end, center, plane, clockwise)

    radius = axes.get("R")
    if radius is None or abs(radius) < _EPS:
        return None
    x0, y0 = start[first], start[second]
    x1, y1 = end[first], end[second]
    dx, dy = x1 - x0, y1 - y0
    chord = math.hypot(dx, dy)
    if chord < _EPS or abs(radius) < chord / 2:
        return None
    height = math.sqrt(max(0.0, radius * radius - (chord / 2) ** 2))
    mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
    perp_x, perp_y = -dy / chord, dx / chord
    candidates = []
    for sign in (1.0, -1.0):
        center = (mid_x + sign * height * perp_x, mid_y + sign * height * perp_y)
        geometry = _geometry_for_center(start, end, center, plane, clockwise)
        if geometry is not None:
            candidates.append(geometry)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # RS274: positive R selects the arc <= 180 degrees, negative R the long one.
    if radius < 0:
        return max(candidates, key=lambda item: abs(item.sweep))
    return min(candidates, key=lambda item: abs(item.sweep))


def _point_at(
    angle: float,
    progress: float,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    geometry: _ArcGeometry,
    plane: int,
) -> tuple[float, float, float]:
    first, second = _PLANE_AXES[plane]
    normal = 3 - first - second
    point = [start[0], start[1], start[2]]
    point[first] = geometry.center[0] + geometry.radius * math.cos(angle)
    point[second] = geometry.center[1] + geometry.radius * math.sin(angle)
    point[normal] = start[normal] + (end[normal] - start[normal]) * progress
    return tuple(point)


def _arc_points(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    geometry: _ArcGeometry,
    plane: int,
) -> tuple[tuple[float, float, float], ...]:
    """Sample one arc, including linear motion along the off-plane axis."""
    points = []
    for index in range(_ARC_SAMPLES):
        progress = index / (_ARC_SAMPLES - 1)
        angle = geometry.start_angle + geometry.sweep * progress
        points.append(_point_at(angle, progress, start, end, geometry, plane))
    points[-1] = end
    return tuple(points)


def _arc_extrema(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    geometry: _ArcGeometry,
    plane: int,
) -> tuple[tuple[float, float, float], ...]:
    """Exact arc extrema for bounds: endpoints plus the four quadrant points."""
    points = [start, end]
    magnitude = abs(geometry.sweep)
    for quadrant in range(4):
        angle = quadrant * math.pi / 2
        if geometry.sweep < 0:
            relative = -((angle - geometry.start_angle) % (-_TWO_PI))
        else:
            relative = (angle - geometry.start_angle) % _TWO_PI
        if relative <= magnitude + _EPS:
            progress = min(1.0, relative / magnitude)
            points.append(
                _point_at(angle, progress, start, end, geometry, plane)
            )
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
            if _is_unsupported_g(value):
                unsupported = True
                result.unsupported_motion = True
                result.warnings.append(
                    f"line {line_number}: G{value:g} can move the machine "
                    "and is not analysed"
                )
                continue
            integer = int(value) if value.is_integer() else None
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

        axes = _scaled(words, "XYZIJKR", scale)
        feed = words["F"] * scale if "F" in words else None
        has_axis = any(letter in axes for letter in "XYZ")
        if not has_axis or unsupported:
            continue

        target = _linear_target(current, axes, absolute)
        if motion in ("G2", "G3"):
            geometry = _arc_geometry(
                current, target, axes, plane, motion == "G2"
            )
            if geometry is None:
                points = (current, target)
                bounds_points = points
                result.warnings.append(
                    f"line {line_number}: arc centre undetermined; "
                    "only endpoints are bounded"
                )
            else:
                points = _arc_points(current, target, geometry, plane)
                bounds_points = _arc_extrema(current, target, geometry, plane)
                result.warnings.append(
                    f"line {line_number}: arc sampled at {_ARC_SAMPLES} points; "
                    "bounds use exact extrema"
                )
        else:
            points = (current, target)
            bounds_points = points

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
        result.bounds = _extend(result.bounds, bounds_points)
        current = target

    return result
