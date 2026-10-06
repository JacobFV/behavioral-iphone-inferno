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
