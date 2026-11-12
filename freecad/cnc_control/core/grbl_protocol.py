"""GRBL 1.1 serial protocol: line parsing and real-time command constants.

Pure Python: no FreeCAD, no Qt.

Sources (verified 2026-11-11):
- https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface
  (response/push messages, status report format, alarm codes)
- https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md
  (real-time command bytes, $ commands)
- https://github.com/gnea/grbl/blob/master/doc/csv/error_codes_en_US.csv
  (error code descriptions)
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Real-time commands (single bytes, sent outside the streaming protocol).
# They never wait in the send/response queue (commands.md).
# ---------------------------------------------------------------------------
CMD_STATUS_QUERY = b"?"
CMD_FEED_HOLD = b"!"
CMD_CYCLE_RESUME = b"~"
CMD_SOFT_RESET = b"\x18"
CMD_SAFETY_DOOR = b"\x84"
CMD_JOG_CANCEL = b"\x85"

FEED_OVERRIDE_COMMANDS = {
    "set_100": b"\x90",
    "increase_10": b"\x91",
    "decrease_10": b"\x92",
    "increase_1": b"\x93",
    "decrease_1": b"\x94",
}
RAPID_OVERRIDE_COMMANDS = {
    "set_100": b"\x95",
    "set_50": b"\x96",
    "set_25": b"\x97",
}
SPINDLE_OVERRIDE_COMMANDS = {
    "set_100": b"\x99",
    "increase_10": b"\x9a",
    "decrease_10": b"\x9b",
    "increase_1": b"\x9c",
    "decrease_1": b"\x9d",
}

# Alarm codes 1-9 (Grbl-v1.1-Interface wiki).
ALARM_DESCRIPTIONS = {
    1: "Hard limit triggered. Machine position is likely lost. Re-homing is highly recommended.",
    2: "G-code motion target exceeds machine travel. Machine position safely retained.",
    3: "Reset while in motion. Grbl cannot guarantee position. Re-homing is highly recommended.",
    4: "Probe fail. Probe not in the expected initial state before starting the probe cycle.",
    5: "Probe fail. Probe did not contact the workpiece within the programmed travel.",
    6: "Homing fail. Reset during active homing cycle.",
    7: "Homing fail. Safety door was opened during active homing cycle.",
    8: "Homing fail. Cycle failed to clear limit switch when pulling off.",
    9: "Homing fail. Could not find limit switch within search distance.",
}

# Error codes 1-38 (doc/csv/error_codes_en_US.csv).
ERROR_DESCRIPTIONS = {
    1: "Expected command letter",
    2: "Bad number format",
    3: "Invalid statement",
    4: "Value < 0",
    5: "Setting disabled (homing)",
    6: "Value < 3 usec",
    7: "EEPROM read fail. Using defaults",
    8: "Not idle",
    9: "G-code lock",
    10: "Homing not enabled",
    11: "Line overflow",
    12: "Step rate > 30kHz",
    13: "Check Door",
    14: "Line length exceeded",
    15: "Travel exceeded",
    16: "Invalid jog command",
    17: "Setting disabled (laser mode)",
    20: "Unsupported command",
    21: "Modal group violation",
    22: "Undefined feed rate",
    23: "G-code command requires an integer value",
    24: "More than one g-code command that requires axis words found in block",
    25: "Repeated g-code word found in block",
    26: "No axis words found in block for commanded motion",
    27: "Line number value is invalid",
    28: "G-code command is missing a required value word",
    29: "G59.x work coordinate systems are not supported",
    30: "G53 only allowed with G0 and G1 motion modes",
    31: "Axis words found in block when no command uses them",
    32: "G2 and G3 arcs require at least one in-plane axis word",
    33: "Motion command target is invalid",
    34: "Arc radius value is invalid",
    35: "G2 and G3 arcs require at least one in-plane offset word",
    36: "Unused value words found in block",
    37: "G43.1 dynamic tool length offset not assigned to configured tool length axis",
    38: "Tool number greater than max supported value",
}

_WELCOME_RE = re.compile(r"^Grbl\s+(\S+)")
_SETTING_RE = re.compile(r"^\$(\S+)=(.+)$")


@dataclass(frozen=True)
class Ok:
    """A line was parsed and executed (or queued)."""


@dataclass(frozen=True)
class Error:
    code: int
    description: str


@dataclass(frozen=True)
class Alarm:
    code: int
    description: str


@dataclass(frozen=True)
class StatusReport:
    """A real-time status report; see the <...> grammar in the Interface wiki."""

    state: str
    sub_state: str | None = None
    mpos: tuple[float, ...] | None = None
    wpos: tuple[float, ...] | None = None
    wco: tuple[float, ...] | None = None
    feed: float | None = None
    spindle: float | None = None
    overrides: tuple[float, float, float] | None = None  # feed, rapid, spindle (%)
    pins: str | None = None


@dataclass(frozen=True)
class Setting:
    code: str
    value: str


@dataclass(frozen=True)
class Feedback:
    """A [KIND:...] push message (MSG, GC, HLP, echo, PRB, ...)."""

    kind: str
    text: str


@dataclass(frozen=True)
class StartupLine:
    """The '>...' line echoed when a startup block executes."""


@dataclass(frozen=True)
class Welcome:
    version: str


@dataclass(frozen=True)
class Unknown:
    text: str


def _floats(text: str) -> tuple[float, ...]:
    return tuple(float(part) for part in text.split(","))


def _parse_status(inner: str) -> StatusReport:
    parts = inner.split("|")
    state, _, sub_state = parts[0].partition(":")
    fields = {}
    for field_text in parts[1:]:
        key, sep, value = field_text.partition(":")
        if not sep:
            continue
        if key in ("MPos", "WPos", "WCO"):
            fields[key.lower()] = _floats(value)
        elif key == "FS":
            feed, _, spindle = value.partition(",")
            fields["feed"] = float(feed)
            fields["spindle"] = float(spindle)
        elif key == "F":
            fields["feed"] = float(value)
        elif key == "Ov":
            fields["overrides"] = tuple(float(x) for x in value.split(","))
        elif key == "Pn":
            fields["pins"] = value
    mpos = fields.get("mpos")
    wpos = fields.get("wpos")
    wco = fields.get("wco")
    # WPos = MPos - WCO per axis (Interface wiki). Compute whichever is missing.
    if mpos is not None and wco is not None and wpos is None:
        wpos = tuple(m - w for m, w in zip(mpos, wco))
    elif wpos is not None and wco is not None and mpos is None:
        mpos = tuple(w + wco for w, wco in zip(wpos, wco))
    return StatusReport(
        state=state,
        sub_state=sub_state or None,
        mpos=mpos,
        wpos=wpos,
        wco=wco,
        feed=fields.get("feed"),
        spindle=fields.get("spindle"),
        overrides=fields.get("overrides"),
        pins=fields.get("pins"),
    )


def parse_line(line: str):
    """Parse one line received from GRBL into a typed result.

    Returns None for empty/whitespace-only lines.
    """
    text = line.strip()
    if not text:
        return None
    if text == "ok":
        return Ok()
    if text.startswith("error:"):
        code = int(text[len("error:"):].strip())
        return Error(code=code, description=ERROR_DESCRIPTIONS.get(code, "Unknown error code"))
    if text.startswith("ALARM:"):
        code = int(text[len("ALARM:"):].strip())
        return Alarm(code=code, description=ALARM_DESCRIPTIONS.get(code, "Unknown alarm code"))
    if text.startswith("<") and text.endswith(">"):
        return _parse_status(text[1:-1])
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        kind, sep, value = inner.partition(":")
        return Feedback(kind=kind if sep else "", text=value if sep else inner)
    if text.startswith(">"):
        return StartupLine()
    match = _WELCOME_RE.match(text)
    if match:
        return Welcome(version=match.group(1))
    match = _SETTING_RE.match(text)
    if match:
        return Setting(code=match.group(1), value=match.group(2).strip())
    return Unknown(text=text)
