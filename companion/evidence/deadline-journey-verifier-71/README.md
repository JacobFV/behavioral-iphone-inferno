# Optional host send deadline verification

Actual run71's guarded counter includes `send_deadline_monotonic`; its original
strict rejection is retained in `owned-guarded-journey-71/strict-postflight.json`.
The verifier now accepts only that one additional optional field, requiring a
finite positive deadline matching the before-send and receiver completion,
coherent receiver write begin/end clocks, a begin strictly before the deadline,
complete exact bytes, no error, and an exact matching control response. The
receiver's write-end-overrun flag must agree with its timestamps. These checks
apply only when the optional field exists; old request schemas retain their
existing checks.

This is a host **write-start** deadline. A complete write may end later if its
recorded overrun flag says so; neither timestamp proves guest delivery. Existing
wire/ACK/capture/normal shutdown checks still apply. Actual71 verifies with a new
output; actual69/70 remain verified. No original report, log, rejection or guest
was changed. Seven explicitly synthetic parsed-copy mutations reject: expired
begin, partial bytes, error, missing clock, mismatched deadline, wrong request ID,
and inconsistent overrun flag. Raw successful run71 itself had no overrun.

The helper's initial no-input failure and minutes of idle during its correction
remain a limitation of run71's full cadence comparison. Verifier success does
not remove that history or classify screenshots.
