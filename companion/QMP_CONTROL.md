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

### Operator-confirmed owned app before capture

The observation-only probe journey waits for a genuine `appeared count=0` serial
marker, then waits for the operator to review the live app at zero. After that
review, request the fixed before capture through the existing QMP owner:

```sh
python3 companion/qmp_control.py --report REPORT probe-capture-before
```

The command accepts exactly `{}` and requires `--probe-journey`. It rejects a
missing appearance marker, an already observed tap1, a repeated request, or the
legacy automatic hardware mode. It sends no input. Then send the separately
controlled tap. A genuine tap1 marker then waits for operator review of visible
counter1 and the exact-empty-arguments `probe-capture-after` command; only that
request captures the after image and completes the journey. The after command
rejects a missing tap marker, missing before capture, or repeated request.
This prevents an early app appearance marker from automatically capturing the
lock screen before the operator has uncovered the app. The explicit legacy
`--probe-hardware-tap` mode retains its previous automatic capture/input sequence.

### Live journey status

`probe-status` accepts exactly `{}` and returns the current in-memory
`ProbeJourney.report` through the private mailbox:

```sh
python3 companion/qmp_control.py --report REPORT probe-status
```

It requires `--probe-journey`, sends no QMP command or input, and does not advance
the journey or capture a frame. The response is a snapshot bounded to4096bytes;
an oversized report is rejected clearly. Use this for live state instead of the
initial `report.json`, which may remain unchanged until the runner finishes.
Previously started runners do not acquire this command automatically.

### Keep a completed journey running

Opt in with `--probe-keep-running --probe-journey --control-mailbox`. The flag
excludes `--probe-hardware-tap`. Default runs still stop on strict completion.
With the flag, a completed journey stays alive until the existing duration limit
or an explicit empty-arguments command:

```sh
python3 companion/qmp_control.py --report REPORT finish-run
```

`finish-run` rejects incomplete journeys and runs without the opt-in. It requests
an orderly loop exit and normal QMP cleanup; it sends no input or process signal.
`probe-status` includes `keep_running` and `finish_requested`. Status is read-only;
the original duration limit is never extended. These options affect new runners
only. Completion still requires genuine guest markers and operator captures.

### Explicit request to reopen the owned app

With `--guest-hid-serial --control-mailbox`, `guest-open-app` accepts exactly
`request_id` (32 lowercase hexadecimal characters) and `boot_uuid` (the exact
current36-character UUID spelling from `INFERNO_OPEN_READY` or the relay):

```sh
python3 companion/qmp_control.py --report REPORT guest-open-app --arguments '{"request_id":"0123456789abcdef0123456789abcdef","boot_uuid":"11111111-2222-3333-4444-555555555555"}'
```

Replace both example identifiers with a fresh request ID and the actual current
boot UUID. No UUID normalization occurs. The sole existing serial connection
sends `INFERNO_OPEN_V1 <request_id> <boot_uuid>\n`. The helper checks the boot
identity and invokes only its fixed owned launcher; no path, arguments, bundle
identifier, process kill, registration or arbitrary command can be supplied.

OPEN and HID share the host replay-rejection set. Eight OPEN attempts per host
run are allowed, including uncertain transmissions. The original guest helper
also bounds attempts and rejects busy, duplicate or foreign-boot requests.
A busy helper does not queue input; neither host nor helper retries automatically.
A host reply proves only serial transmission. `INFERNO_OPEN_DISPATCHED` proves
fork only; original launch callback/timing and visual observation determine
acceptance. `INFERNO_OPEN_CHILD_END` reports child status. Inspect raw logs before
any new explicit request, especially after an uncertain send.
