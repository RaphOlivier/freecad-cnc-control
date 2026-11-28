"""E8: pre-job checks against machine travel from $$ settings."""

from freecad.cnc_control.core.gcode import analyze
from freecad.cnc_control.core.preflight import MachineLimits, check_job


def limits() -> MachineLimits:
    return MachineLimits((200.0, 200.0, 100.0))


def test_machine_limits_from_settings():
    parsed = MachineLimits.from_settings(
        {"130": 200.0, "131": 200.0, "132": 100.0, "20": 1.0}
    )
    assert parsed is not None
    assert parsed.travel == (200.0, 200.0, 100.0)
    assert parsed.soft_limits_enabled is True
    assert MachineLimits.from_settings({"130": 200.0}) is None
    assert MachineLimits.from_settings({"130": 0.0, "131": 1.0, "132": 1.0}) is None


def test_job_within_limits_is_accepted_but_not_confirmed():
    result = check_job(analyze(["G21 G90", "G1 X10 Y10"]), limits())
    assert result.accepted is True
    assert result.requires_confirmation is True
    assert result.suggest_check_mode is True
    assert result.as_dict()["bounds"]["x"] == [0.0, 10.0]
    assert result.as_dict()["segments"] == 1


def test_job_outside_limits_is_refused():
    result = check_job(analyze(["G21 G90", "G1 X300"]), limits())
    assert result.accepted is False
    assert any("X travel 300" in reason for reason in result.reasons)
    assert result.requires_confirmation is False
    assert result.suggest_check_mode is False


def test_missing_machine_limits_refuse_the_job():
    result = check_job(analyze(["G21 G90", "G1 X1"]), None)
    assert result.accepted is False
    assert any("$130" in reason for reason in result.reasons)


def test_unsupported_motion_refuses_the_job():
    result = check_job(analyze(["G21 G90", "G28 X0 Y0"]), limits())
    assert result.accepted is False
    assert any("G28" in warning for warning in result.warnings)


def test_empty_program_refuses_the_job():
    result = check_job(analyze(["(no motion)"]), limits())
    assert result.accepted is False
    assert any("no analysed motion" in reason for reason in result.reasons)


def test_confirmation_requirement_can_be_disabled_by_policy():
    result = check_job(
        analyze(["G21 G90", "G1 X1"]), limits(), require_confirmation=False
    )
    assert result.accepted is True
    assert result.requires_confirmation is False
    assert result.suggest_check_mode is True
