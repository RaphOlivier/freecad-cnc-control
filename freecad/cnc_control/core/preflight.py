"""Pre-job safety checks for GRBL programs.

Pure Python: no FreeCAD, no Qt. The checks use the machine travel reported by
``$$`` ($130/$131/$132), the current work offset from the status report, and
the G-code analysis from core/gcode.py.

Program coordinates are shifted by the work offset before being compared with
machine travel. If the controller does not report WCO or WPos/MPos, the check
refuses the job rather than guessing.

A preflight result never starts a job: the GUI must ask for explicit
confirmation and may offer GRBL check mode ($C) first.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from freecad.cnc_control.core.gcode import GcodeAnalysis

_MAX_TRAVEL_CODES = ("130", "131", "132")
_TOLERANCE_MM = 1e-6
_FORBIDDEN_LINE_CHARS = frozenset("$!~?")


@dataclass(frozen=True)
class MachineLimits:
    """Maximum travel per axis, in millimetres, from GRBL settings."""

    travel: tuple[float, float, float]
    soft_limits_enabled: bool = False

    @classmethod
    def from_settings(cls, settings: dict[str, float]) -> MachineLimits | None:
        """Build limits from ``$$`` values; None when an axis is missing."""
        values = []
        for code in _MAX_TRAVEL_CODES:
            value = settings.get(code)
            if value is None:
                return None
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None
            if number <= 0:
                return None
            values.append(number)
        return cls(tuple(values), float(settings.get("20", 0.0)) != 0.0)

    def as_dict(self) -> dict[str, object]:
        """JSON-ready summary for worker events."""
        return {
            "travel": list(self.travel),
            "soft_limits_enabled": self.soft_limits_enabled,
        }


@dataclass
class PreflightResult:
    """Outcome of a pre-job check; accepted does not mean confirmed."""

    accepted: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    suggest_check_mode: bool = False
    analysis: GcodeAnalysis | None = None
    limits: MachineLimits | None = None
    work_offset: tuple[float, float, float] | None = None

    def as_dict(self) -> dict[str, object]:
        """JSON-ready summary, without the full segment list."""
        bounds = self.analysis.bounds if self.analysis is not None else None
        return {
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "requires_confirmation": self.requires_confirmation,
            "suggest_check_mode": self.suggest_check_mode,
            "bounds": bounds.as_dict() if bounds is not None else None,
            "segments": len(self.analysis.segments) if self.analysis else 0,
            "operations": list(self.analysis.operations) if self.analysis else [],
            "limits": self.limits.as_dict() if self.limits is not None else None,
            "work_offset": list(self.work_offset) if self.work_offset is not None else None,
        }


def validate_job_lines(lines: Iterable[str]) -> list[str]:
    """Refuse lines that could bypass preflight or inject real-time bytes.

    GRBL interprets ``$`` commands and single real-time bytes anywhere in the
    incoming stream, including inside a job line. Such lines must never reach
    the character-counting streamer.
    """
    reasons: list[str] = []
    for number, line in enumerate(lines, start=1):
        if not isinstance(line, str):
            reasons.append(f"line {number}: not a text line")
            continue
        if any(ord(char) < 0x20 or ord(char) > 0x7E for char in line):
            reasons.append(f"line {number}: control or non-ASCII byte")
            continue
        forbidden = sorted(_FORBIDDEN_LINE_CHARS.intersection(line))
        if forbidden:
            reasons.append(
                f"line {number}: forbidden command byte(s) {''.join(forbidden)}"
            )
    return reasons


def check_job(
    analysis: GcodeAnalysis,
    limits: MachineLimits | None,
    require_confirmation: bool = True,
    work_offset: tuple[float, float, float] | None = None,
) -> PreflightResult:
    """Refuse unsafe programs; never authorise a real run by itself."""
    reasons: list[str] = []
    warnings = list(analysis.warnings)

    if analysis.bounds is None:
        reasons.append("the program contains no analysed motion")
    if analysis.unsupported_motion:
        reasons.append("the program contains unanalysed motion-changing commands")
    if limits is None:
        reasons.append("machine travel is unavailable ($$ $130..$132)")
    if work_offset is None:
        reasons.append("work offset is unavailable from the status report")

    if analysis.bounds is not None and limits is not None and work_offset is not None:
        for index, axis in enumerate("XYZ"):
            minimum = analysis.bounds.minimum[index] + work_offset[index]
            maximum = analysis.bounds.maximum[index] + work_offset[index]
            extent = max(abs(minimum), abs(maximum))
            if extent > limits.travel[index] + _TOLERANCE_MM:
                reasons.append(
                    f"{axis} travel {extent:.3f} mm exceeds "
                    f"{limits.travel[index]:.3f} mm"
                )

    accepted = not reasons
    return PreflightResult(
        accepted=accepted,
        reasons=reasons,
        warnings=warnings,
        requires_confirmation=accepted and require_confirmation,
        suggest_check_mode=accepted,
        analysis=analysis,
        limits=limits,
        work_offset=work_offset,
    )
