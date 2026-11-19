# Failures log

Rule 3 of the working rules: three failed attempts on the same point = stop and report.

## 2026-11-11 - E3: tests hung (19 min) then blocked again after rewrite

- Symptom 1 (owner PC): pytest hung 19 minutes; KeyboardInterrupt. Cause: FakeGrbl line buffer was `bytes` (no `.append()`) so the serve thread crashed and clients blocked forever.
- Symptom 2 (Codespace): tests hung again at the multi-line `$$` response. Cause: `Transport.read_line()` only consumed its buffer after new bytes arrived, so lines already buffered were stranded when the controller sent several lines in one chunk.
- Fixes: line buffer is a `bytearray`; `read_line()` checks the buffer before blocking on `read()`. Tests bounded with `timeout 120`.
- Lesson: any blocking read helper must drain its buffer before waiting; test suites must always run under a timeout.

## 2026-11-11 - E3: test_pty_conversation hung (3rd attempt, root cause found)

- Symptom: all tests pass except test_pty_conversation, which blocks after the first two steps.
- Root cause: the pty slave line discipline is in canonical mode by default; bytes without a newline (real-time commands like '?') are never delivered to the reader, so the fake GRBL never sees the status query.
- Fix: clear ICANON (and ECHO) on the slave at open().
- Lesson: a pty is not a dumb pipe; its line discipline must be configured to emulate a serial link.

## 2026-11-11 - E4: 2 test failures + 1 hang on first run

- Push messages (banner, [MSG:...]) were releasing a pending line; only ok/error acknowledge (Interface wiki). Fixed: ack only on Ok/Error.
- Test bug: called read(timeout=...) which does not exist; fixed the test.
- Hang: a line that can never fit the RX buffer blocked run() forever on read_line; fixed: stop the stream, never send that line.
- Lesson: distinguish ack-carrying responses from push messages before writing the accounting; a streamer must detect unsendable lines instead of waiting.

## 2026-11-18 - E6: connect event never fired in 2 tests

- Symptom: test_connect_and_version and test_disconnect_and_shutdown_events timed out waiting for "connected".
- Root cause: the fake GRBL was started after waiting for the handshake to complete; the worker blocked reading a banner nobody sends yet.
- Fix: start the fake inside the transport factory, before connect() runs.
- Lesson: in handshake tests, start the peer side before waiting for handshake events.
