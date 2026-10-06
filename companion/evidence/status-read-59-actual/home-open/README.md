# Third and fourth windows: Home and explicit OPEN

The retained log is only the additional immutable bytes [345699,459473); prior prefixes remain untouched. `python3 audit.py` checks ordered read/W1C pairs, source-line hashes and offsets, raw QMP successes for each set of eight enables/disables, and exact named OPEN serial wire. There is no duplicate full event index.

Home bracket [345699,409395) contains 63,696 bytes, 28 reads/W1C pairs (18 output-ready 0x400, ten frame-processed 0x100000), ten submits and 28 unknown45004 zero reads. Its start is the previous counter-after checkpoint, **not** a just-before-Home checkpoint. Thus the entire bracket must not be attributed to the Home action. The original VNC report records F6 down at 1791329392.3497636 and release at 9392.4998605; no pointer event.

OPEN bracket [409395,459473) contains 50,078 bytes, 32 reads/W1C pairs (25 output-ready, seven frame-processed), seven submits and 32 unknown45004 zero reads. Submission trace-before409395 is at 1791329439.1201758. Exact request 062c71ec8bfb4287b2627b0569cddd9f was sent at 9439.2522979. Parent separately reviewed the reopened app retaining counter1 and derived warm lifecycle timing; this display audit does not substitute trace timing for that lifecycle measurement.

In both brackets every sampled status read is immediately followed among ADP events by an identical W1C, with before equal to the value and after zero. Neither bracket contains zero or mixed-bit status reads. Eight enables and disables for each window match actual QMP replies. No HMP/register-query/input QMP command appears in the retained sole-owner QMP prefix; explicit VNC Home and serial OPEN are preserved separately.

All referenced Home and after-OPEN PNG hashes were checked; visual semantics remain the parent's independent review. VNC refresh, buffered trace visibility and missing per-event clocks prohibit per-action draw attribution, presentation-latency or freeze-fix claims. Unknown45004 reads returning zero are correlated observations, not a decoded hardware function.
