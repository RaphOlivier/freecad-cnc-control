"""Convert FreeCAD CAM commands to GRBL 1.1 G-code.

Pure Python: no FreeCAD, no Qt. The adapter turns CAM objects into
:class:`CamOperation` instances; this module only formats safe G-code lines.
It emits ``(OP: name)`` markers understood by :mod:`core.gcode` and drops
commands that the pre-job checks refuse (G10, G28, G30, G38.x, G43.x, G53,
G92.x and tool changes). Nothing here opens a link or moves a machine.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

MM_PER_INCH = 25.4

_WORD_RE = re.compile(r"^([A-Za-z])(\d+(?:\.\d+)?)$")
_CODE_RE = re.compile(r"([A-Za-z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
_COMMENT_RE = re.compile(r"\(.*?\)|;.*$")
_UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 _./:-]+")

_SUPPORTED_G = frozenset({0, 1, 2, 3, 4, 17, 18, 19, 54, 55, 56, 57, 58, 59, 90, 91, 93, 94})
_SUPPORTED_M = frozenset({2, 3, 4, 5, 8, 9, 30})
_UNSUPPORTED_G = frozenset({10, 28, 30, 38, 43, 53, 92})
_UNSUPPORTED_M = frozenset({6})
_SCALED_PARAMETERS = frozenset("XYZIJKRF")
_PARAMETER_ORDER = ("X", "Y", "Z", "I", "J", "K", "R", "F", "P", "S")
_ALLOWED_PARAMETERS = frozenset(_PARAMETER_ORDER)


@dataclass(frozen=True)
class CamCommand:
    """One CAM command: a G/M code and letter/value parameters."""

    name: str
    parameters: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CamOperation:
    """One active CAM operation with its ordered commands."""

    name: str
    commands: Iterable[CamCommand]


@dataclass
class PostResult:
    """Output of one post-processing run, including skipped-command warnings."""

    lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    operations: list[str] = field(default_factory=list)


def safe_operation_name(name: str) -> str:
    """Return an ASCII label usable in a GRBL job comment."""
    cleaned = " ".join(_UNSAFE_NAME_RE.sub(" ", str(name)).split())
    return (cleaned[:80] or "Operation")


def command_from_line(line: str) -> CamCommand | None:
    """Parse a raw G-code line into a :class:`CamCommand`."""
    code = _COMMENT_RE.sub(" ", line).strip()
    words = [(letter.upper(), float(value)) for letter, value in _CODE_RE.findall(code)]
    for index, (letter, value) in enumerate(words):
        if letter in "GM":
            parameters = {
                other: number
                for position, (other, number) in enumerate(words)
                if position != index
            }
            return CamCommand(f"{letter}{value:g}", parameters)
    return None


def _parse_name(name: str) -> tuple[str, int] | None:
    match = _WORD_RE.fullmatch(name.strip())
    if match is None:
        return None
    letter = match.group(1).upper()
    if letter not in "GM":
        return None
    number = float(match.group(2))
    if not number.is_integer():
        return None
    return letter, int(number)


def _format_parameters(parameters: Mapping[str, float], scale: float) -> str | None:
    output: list[str] = []
    for letter in _PARAMETER_ORDER:
        if letter not in parameters:
            continue
        value = parameters[letter]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if not math.isfinite(value):
            return None
        factor = scale if letter in _SCALED_PARAMETERS else 1.0
        output.append(f"{letter}{value * factor:g}")
    return "".join(output)


def post_process(operations: Iterable[CamOperation], *, header: bool = True) -> PostResult:
    """Format active CAM operations as GRBL-safe G-code lines."""
    result = PostResult()
    if header:
        result.lines.extend(["(CNC Control GRBL program)", "G21", "G90"])
    scale = 1.0

    for operation in operations:
        label = safe_operation_name(operation.name)
        result.operations.append(label)
        result.lines.append(f"(OP: {label})")
        for command in operation.commands:
            parsed = _parse_name(command.name)
            if parsed is None:
                result.warnings.append(
                    f"{label}: unsupported command {command.name!r} skipped"
                )
                continue
            letter, number = parsed
            if letter == "G" and number in _UNSUPPORTED_G:
                result.warnings.append(
                    f"{label}: G{number} skipped (refused by preflight)"
                )
                continue
            if letter == "M" and number in _UNSUPPORTED_M:
                result.warnings.append(f"{label}: M{number} skipped (tool change)")
                continue
            if letter == "G" and number == 20:
                scale = MM_PER_INCH
                continue  # values are converted to mm, the program stays metric
            if letter == "G" and number == 21:
                scale = 1.0
                continue
            supported = _SUPPORTED_G if letter == "G" else _SUPPORTED_M
            if number not in supported:
                result.warnings.append(
                    f"{label}: {letter}{number} skipped (unsupported by GRBL)"
                )
                continue
            if not set(command.parameters).issubset(_ALLOWED_PARAMETERS):
                result.warnings.append(
                    f"{label}: {letter}{number} skipped (unsupported parameter)"
                )
                continue
            parameters = _format_parameters(command.parameters, scale)
            if parameters is None:
                result.warnings.append(
                    f"{label}: {letter}{number} skipped (invalid parameter)"
                )
                continue
            result.lines.append(f"{letter}{number}{parameters}")

    return result
