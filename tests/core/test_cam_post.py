"""Pure-Python GRBL post-processing of fabricated CAM operations."""

from freecad.cnc_control.core.cam_post import (
    CamCommand,
    CamOperation,
    command_from_line,
    post_process,
    safe_operation_name,
)
from freecad.cnc_control.core.gcode import analyze
from freecad.cnc_control.core.preflight import MachineLimits, check_job


def test_operation_markers_and_motion_lines():
    operations = [
        CamOperation(
            "Roughing",
            [
                CamCommand("G0", {"X": 1, "Y": 2}),
                CamCommand("G1", {"Z": -2, "F": 100}),
                CamCommand("M3", {"S": 1000}),
            ],
        )
    ]

    result = post_process(operations)

    assert result.lines == [
        "(CNC Control GRBL program)",
        "G21",
        "G90",
        "(OP: Roughing)",
        "G0X1Y2",
        "G1Z-2F100",
        "M3S1000",
    ]
    assert result.operations == ["Roughing"]
    assert result.warnings == []
    analysis = analyze(result.lines)
    assert analysis.operations == ["Roughing"]
    assert analysis.unsupported_motion is False


def test_preflight_accepts_a_post_processed_program():
    operations = [
        CamOperation(
            "Pocket",
            [
                CamCommand("G0", {"X": 5, "Y": 5}),
                CamCommand("G1", {"X": 10, "F": 200}),
            ],
        )
    ]
    result = post_process(operations)

    analysis = analyze(result.lines)
    limits = MachineLimits((100.0, 100.0, 100.0))
    report = check_job(analysis, limits, work_offset=(0.0, 0.0, 0.0))

    assert report.accepted is True
    assert report.requires_confirmation is True
    assert "Pocket" in report.as_dict()["operations"]


def test_unsafe_codes_are_skipped_with_warnings():
    operations = [
        CamOperation(
            "Op",
            [
                CamCommand("G28", {}),
                CamCommand("G38.2", {"Z": -5}),
                CamCommand("M6", {"T": 1}),
                CamCommand("G10", {"X": 1}),
                CamCommand("G92", {"X": 0}),
                CamCommand("G1", {"X": 1, "F": 100}),
            ],
        )
    ]

    result = post_process(operations)

    assert result.lines[-1] == "G1X1F100"
    assert len(result.warnings) == 5
    assert all("skipped" in warning for warning in result.warnings)
    assert not any("G28" in line or "G38" in line for line in result.lines)
    assert analyze(result.lines).unsupported_motion is False


def test_inch_values_are_converted_to_millimetres():
    operations = [
        CamOperation(
            "Inch",
            [
                CamCommand("G20", {}),
                CamCommand("G1", {"X": 1, "F": 10}),
                CamCommand("G21", {}),
                CamCommand("G1", {"X": 1}),
            ],
        )
    ]

    result = post_process(operations)

    assert "G20" not in result.lines
    assert "G1X25.4F254" in result.lines
    assert result.lines[-1] == "G1X1"


def test_operation_names_are_safe_ascii_comments():
    assert safe_operation_name("Pocket ($) ?\n") == "Pocket"
    assert safe_operation_name("!!!") == "Operation"

    result = post_process([CamOperation("A/B: C", [])])

    assert result.lines[-1] == "(OP: A/B: C)"


def test_command_from_line_parses_words_and_ignores_comments():
    assert command_from_line("G1 X2 Y-3 F100 (note)") == CamCommand(
        "G1", {"X": 2.0, "Y": -3.0, "F": 100.0}
    )
    assert command_from_line("(only a comment)") is None
