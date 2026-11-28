"""Pre-job safety checks for GRBL programs.

Pure Python: no FreeCAD, no Qt. The checks use the machine travel reported by
``$$`` ($130/$131/$132) and the G-code analysis from core/gcode.py.

Work offsets are not applied by the analyser, so the travel check compares
the largest absolute program coordinate per axis with the reported maximum
travel. This is a conservative approximation, not a substitute for knowing
the real work coordinate system.

A preflight result never starts a job: the GUI must ask for explicit
confirmation and may offer GRBL check mode ($C) first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from freecad.cnc_control.core.gcode import GcodeAnalysis

_MAX_TRAVEL_CODES = ("130", "131", "132")
_TOLERANCE_MM = 1e-6


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
            if value is None or value <= 0:
                return None
            values.append(value)
        return cls(tuple(values), settings.get("20", 0.0) != 0)

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
        }


def check_job(
    analysis: GcodeAnalysis,
    limits: MachineLimits | None,
    require_confirmation: bool = True,
) -> PreflightResult:
    """Refuse unsafe programs; never authorise a real run by itself."""
    reasons: list[str] = []
    warnings = list(analysis.warnings)

    if analysis.bounds is None:
        reasons.append("the program contains no analysed motion")
    if limits is None:
        reasons.append("machine travel is unavailable ($$ $130..$132)")
    if analysis.bounds is not None and limits is not None:
        for index, axis in enumerate("XYZ"):
            extent = max(
                abs(analysis.bounds.minimum[index]),
                abs(analysis.bounds.maximum[index]),
            )
            if extent > limits.travel[index] + _TOLERANCE_MM:
                reasons.append(
                    f"{axis} travel {extent:.3f} mm exceeds "
                    f"{limits.travel[index]:.3f} mm"
                )

    accepted = not reasons
    warnings.insert(
        0,
        "work offsets are not applied: bounds are in program coordinates",
    )
    return PreflightResult(
        accepted=accepted,
        reasons=reasons,
        warnings=warnings,
        requires_confirmation=accepted and require_confirmation,
        suggest_check_mode=accepted,
        analysis=analysis,
        limits=limits,
    )
