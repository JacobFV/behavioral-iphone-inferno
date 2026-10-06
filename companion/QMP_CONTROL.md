# Private input diagnostics

Start a bounded boot with `--control-mailbox`. The runner creates its report's
`control/` directory with mode 0700 and polls requests through its existing QMP
connection. Every boot also records initial `query-mice` in the QMP transcript.
No second QMP connection or network listener is created.

```
python3 companion/qmp_control.py --report /absolute/report query-mice
python3 companion/qmp_control.py --report /absolute/report trace-event-get-state --arguments '{"name":"input_event_abs"}'
python3 companion/qmp_control.py --report /absolute/report trace-event-set-state --arguments '{"name":"input_event_abs","enable":true}'
python3 companion/qmp_control.py --report /absolute/report input-send-event --arguments '{"events":[{"type":"abs","data":{"axis":"x","value":16384}},{"type":"abs","data":{"axis":"y","value":16384}}]}'
```

Only `query-mice`, trace get/set for the names in `TRACE_EVENTS`, and one to eight
absolute x/y (0–32767) or left-button events per request are accepted. The six
`apple_mt_spi_*` names require the matching instrumented build. Enable tracing
only for a bounded gesture window and disable it afterward. Pointer press and
release are separate explicit requests; the operator must release after a press.
Coordinate one input owner with the automatic probe journey and VNC operator.

Requests and replies are owned mode-0600 regular JSON files, maximum 4096 bytes;
requests expire after 30 seconds. The client waits at most 35 seconds. Both the
original raw request plus its hash and the reply remain in
`control-transcript.jsonl`; accepted QMP commands additionally appear in the raw
`qmp-transcript.jsonl`. Rejected commands never reach QMP. A lost client response
does not prove that an accepted request was unexecuted: inspect the transcripts
before retrying input. The mailbox grants no arbitrary QMP or keyboard commands.

A real firmware-free QMP plumbing check recorded query-mice, trace get/set and a
rejected quit command. Its deliberately stopped empty machine rejected pointer
input with `VM not running`. This check is not evidence of guest touch delivery;
that requires the actual guest traces and visible response.

`--touch-trace-startup` enables exactly the six touch-model tracepoints through
QMP before `cont`. The runner records start/deadline and enable/disable replies,
and disables them after 180 seconds or earlier cleanup.
`--touch-trace-seconds N` selects an integer limit from 1 to 1800 seconds and
requires `--touch-trace-startup`. Use a longer bounded window when original
userspace firmware delivery starts after the default interval. With `--guest-errors`,
trace output shares `guest-errors.log`; otherwise it uses `touch-trace.log`.
This observes the existing device behavior without changing it.

The private `query-touch-registers` alias takes no arguments. It issues seven
fixed `human-monitor-command` requests: `xp /1wx` at GPIO `0x24a820088`, and SPI1
`0x235104000`, `0x235104004`, `0x235104008`, `0x23510400c`, `0x235104034`,
`0x23510404c`. These individual register reads were reviewed as nondestructive.
RXDATA (`+0x20`) and bulk reads are excluded. There is no general monitor-command
entry point. Each underlying request/reply appears in the raw QMP transcript;
the combined alias response remains subject to the 4096-byte limit.

```
python3 companion/qmp_control.py --report /absolute/report query-touch-registers
```

## Optional owned-harness serial channel

`--guest-hid-serial --control-mailbox` replaces only that boot's `serial=file`
backend with a private Unix socket chardev. The default remains unchanged. The
runner connects before `cont` and continuously drains output on a dedicated
thread, because the UART model's `write_all` can block if a connected reader
stops draining. QEMU writes unchanged output to `serial.log` with no inserted
timestamps. The Unix socket is mode 0600 in the runner's private mode 0700 temporary
directory. There is no network listener or second QMP connection. Cleanup closes
the socket and bounds the drain-thread join to two seconds.

The `guest-hid-gesture` mailbox command accepts exactly one of these objects:

```
{"kind":"tap","request_id":"0123456789abcdef0123456789abcdef","x":16384,"y":16384,"duration_ms":100}
{"kind":"swipe","request_id":"abcdef0123456789abcdef0123456789","x0":16384,"y0":30000,"x1":16384,"y1":12000,"duration_ms":1000}
```

Use a new 32-character lowercase hexadecimal request ID for every explicit
request. Coordinates must be integers 0..32767 and duration must be 1..2000 ms.
Additional keys, arbitrary strings, control bytes and commands are rejected.
The fixed wire grammar, agreed with the owned guest helper, is:

```
INFERNO_HID_V1 <id> TAP <x> <y> <duration_ms>\n
INFERNO_HID_V1 <id> SWIPE <x0> <y0> <x1> <y1> <duration_ms>\n
```

Each ASCII line is at most 160 bytes including its newline. The guest helper's
backend is independent of this transport; the host sends no input automatically.
Duplicate IDs are refused for the entire run, even after an uncertain partial
send. Before-send and after-send records, exact line bytes and hashes are retained
in mode 0600 `serial-input-transcript.jsonl`, alongside the mailbox journal.
A successful host response means only `written-to-serial-socket`. A guest
`INFERNO_HID_ACK` means an attempted operation; neither proves UI acceptance.
Inspect the serial acknowledgment and actual framebuffer before assessing the
result. Never automatically replay a request whose outcome is uncertain.

An actual firmware-free transport check attached the socket chardev to an empty
QEMU monitor frontend: two fixed gesture lines arrived and were echoed/rejected
as unknown monitor commands, duplicate/extra-key requests were refused locally,
raw output was logged and the drain thread stopped cleanly. That is a socket/log
plumbing check, not a guest UART, console-read or HID test. Those require the
original guest and the owned helper to execute.

## Owned app journey observation

`--probe-journey` observes the owned app's appearance and operator-produced tap
markers, captures `probe-before.ppm` and `probe-after.ppm`, and still fails an
incomplete journey. It sends no input by default. The operator must review the
first capture and use the explicitly requested input route; captures still need
visual review even when the markers complete the observation.

The old hardware-input experiment requires the separate explicit
`--probe-hardware-tap` flag. It cannot be combined with `--guest-hid-serial`, and
the hardware SPI consumption problem makes it unsuitable for the current guest.
Reports record `input_mode` and `automatic_input`. Previously loaded runners keep
their original behavior until stopped; changing this source does not hot-patch a
live run.
