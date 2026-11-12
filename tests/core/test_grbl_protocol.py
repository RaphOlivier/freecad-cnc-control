"""Tests for GRBL 1.1 protocol parsing, from official documentation examples."""

from freecad.cnc_control.core import grbl_protocol as gp


def test_ok():
    assert isinstance(gp.parse_line("ok"), gp.Ok)


def test_empty_line_returns_none():
    assert gp.parse_line("") is None
    assert gp.parse_line("   \r\n") is None


def test_error_with_known_code():
    result = gp.parse_line("error:9")
    assert result == gp.Error(code=9, description="G-code lock")


def test_error_with_unknown_code():
    result = gp.parse_line("error:99")
    assert result.code == 99
    assert "Unknown" in result.description


def test_alarm_with_description():
    result = gp.parse_line("ALARM:1")
    assert result == gp.Alarm(code=1, description=gp.ALARM_DESCRIPTIONS[1])
    assert "Hard limit" in result.description


def test_welcome_message():
    result = gp.parse_line("Grbl 1.1h ['$' for help]")
    assert result == gp.Welcome(version="1.1h")


def test_startup_line():
    assert isinstance(gp.parse_line(">G54G20G90G94M5M9"), gp.StartupLine)


def test_status_mpos_and_fs():
    result = gp.parse_line("<Idle|MPos:0.000,0.000,0.000|FS:0.0,0>")
    assert result.state == "Idle"
    assert result.mpos == (0.0, 0.0, 0.0)
    assert result.feed == 0.0
    assert result.spindle == 0.0
    assert result.wpos is None


def test_status_hold_sub_state():
    result = gp.parse_line("<Hold:1|MPos:1.000,2.000,3.000>")
    assert result.state == "Hold"
    assert result.sub_state == "1"


def test_status_wpos_with_wco_computes_mpos():
    result = gp.parse_line("<Run|WPos:1.000,2.000,3.000|WCO:10.000,20.000,30.000>")
    assert result.mpos == (11.0, 22.0, 33.0)
    assert result.wpos == (1.0, 2.0, 3.0)


def test_status_mpos_with_wco_computes_wpos():
    result = gp.parse_line("<Idle|MPos:11.000,22.000,33.000|WCO:10.000,20.000,30.000>")
    assert result.wpos == (1.0, 2.0, 3.0)


def test_status_overrides_and_pins():
    result = gp.parse_line("<Run|MPos:0.000,0.000,0.000|FS:500.0,10000|Ov:110,100,90|Pn:XYZ>")
    assert result.overrides == (110.0, 100.0, 90.0)
    assert result.pins == "XYZ"
    assert result.feed == 500.0


def test_feedback_msg():
    result = gp.parse_line("[MSG:Reset to continue]")
    assert result == gp.Feedback(kind="MSG", text="Reset to continue")


def test_feedback_gc():
    result = gp.parse_line("[GC:G0 G54 G17 G21 G90 G94 M0 M5 M9 T0 S0.0 F500.0]")
    assert result.kind == "GC"
    assert result.text.startswith("G0 G54")


def test_setting():
    result = gp.parse_line("$130=200.000")
    assert result == gp.Setting(code="130", value="200.000")


def test_unknown_line():
    result = gp.parse_line("something unexpected")
    assert isinstance(result, gp.Unknown)
    assert result.text == "something unexpected"


def test_realtime_constants():
    assert gp.CMD_FEED_HOLD == b"!"
    assert gp.CMD_CYCLE_RESUME == b"~"
    assert gp.CMD_SOFT_RESET == b"\x18"
    assert gp.CMD_JOG_CANCEL == b"\x85"
    assert gp.CMD_STATUS_QUERY == b"?"
    assert len(gp.FEED_OVERRIDE_COMMANDS) == 5
    assert len(gp.RAPID_OVERRIDE_COMMANDS) == 3
    assert len(gp.SPINDLE_OVERRIDE_COMMANDS) == 5
