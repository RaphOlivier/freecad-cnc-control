"""E7: G-code analysis (bounds, path, source mapping, operation names)."""

import pytest

from freecad.cnc_control.core.gcode import analyze


def test_linear_motion_builds_bounds_and_line_map():
    analysis = analyze(
        [
            "(Operation: Roughing)",
            "G21 G90",
            "G0 X10 Y20",
            "G1 X30 Y40 F100",
        ]
    )
    assert analysis.units == "mm"
    assert analysis.operations == ["Roughing"]
    assert analysis.command_count == 3
    assert len(analysis.segments) == 2
    assert analysis.line_segments == {3: [0], 4: [1]}
    assert analysis.bounds.minimum == (0.0, 0.0, 0.0)
    assert analysis.bounds.maximum == (30.0, 40.0, 0.0)
    assert analysis.segments[0].motion == "G0"
    assert analysis.segments[1].motion == "G1"
    assert analysis.segments[1].feed == 100.0
    assert analysis.segments[1].operation == "Roughing"


def test_inches_and_incremental_are_converted_to_millimetres():
    analysis = analyze(["G20 G91", "G1 X1 Y2", "G1 X-0.5 Z1"])
    assert analysis.units == "in"
    assert analysis.bounds.minimum == pytest.approx((0.0, 0.0, 0.0))
    assert analysis.bounds.maximum == pytest.approx((25.4, 50.8, 25.4))


def test_arc_is_sampled_and_its_full_extent_is_in_bounds():
    analysis = analyze(["G21 G90 G17", "G0 X0 Y0", "G2 X10 Y0 I5 J0"])
    assert len(analysis.segments) == 2
    arc = analysis.segments[1]
    assert arc.motion == "G2"
    assert len(arc.points) == 9
    assert max(point[1] for point in arc.points) == pytest.approx(5.0)
    assert analysis.bounds.maximum[1] == pytest.approx(5.0)
    assert analysis.bounds.maximum[0] == pytest.approx(10.0)
    assert any("arc sampled" in warning for warning in analysis.warnings)


def test_semicolon_comments_and_operation_names():
    analysis = analyze(["; header", "(OP: Finish)", "G1 X1 ; trailing comment"])
    assert analysis.operations == ["Finish"]
    assert analysis.command_count == 1
    assert analysis.segments[0].operation == "Finish"


def test_unsupported_motion_is_warned_and_not_analysed():
    analysis = analyze(["G21 G90", "G28 X0 Y0", "G1 X1"])
    assert len(analysis.segments) == 1
    assert analysis.segments[0].end == (1.0, 0.0, 0.0)
    assert any("G28" in warning for warning in analysis.warnings)


def test_empty_program_has_no_bounds():
    analysis = analyze(["", "(just a comment)"])
    assert analysis.bounds is None
    assert analysis.segments == []
    assert analysis.command_count == 0
