# Explicit recovered-journey verification

This replay implements the reviewed run67 design. It verifies only a named,
new-process recovery journey; it does not convert the failed initial launch or
whole boot into a pass. No guest actions or original evidence edits occurred.

```
companion/run verify-journey --report /absolute/app-boot-67 \
  --recovery-open-request f657a4fdfee94393a5dd721690eadf30 \
  --output /new/recovered-journey.json
```

The explicit mode binds the host OPEN, exact serial transmission, guest dispatch,
accepted callback and normal launcher exit. It requires a distinct original-libproc
app identity and five validated hooks whose main follows that request and whose
last hook precedes its callback. Every lifecycle record is paired with its raw
record and validation, including later counter2/3/4 records. Prior incarnations
are permitted only as validated main-only prefixes. Their timing hooks and all
rejection lines remain in the result. A prior appeared/tap marker is rejected;
this narrow mode cannot manufacture historical marker-arrival evidence.

Existing capture hashes, one counter tap/ACK, source-gated capture ordering and
normal QMP shutdown checks remain required. Success is named
`verified-recovered-journey`, with `whole_boot_verified: false`. Visual review is
still a separate human/operator observation; TCP peer identity is unauthenticated.
Default mode and initial/warm timing tools are unchanged.

`results.json` contains six actual read-only replays and seven explicitly
synthetic in-memory association mutations. Actual67 passes only with the named
OPEN; default67 retains its duplicate-main rejection. Default66/59 pass.
Failed64 and failed65 (even with recovery requested) reject missing completion.
The synthetic cases alter only parsed copies: wrong wire, launcher, missing
identity, duplicate malformed OPEN, prior appeared, missing validation, and main
before OPEN. All reject; original reports and logs remain untouched.

The implementation initially expected a nested control response. Actual replay
candidate1 rejected that incorrect assumption; the original response is a direct
serial-transmission result. Candidate2 corrected the binding; candidate3 added
validation of all event records; candidate4 also rejects malformed duplicate
named OPEN records. Their retained outputs remain outside Git under run67.
`replay.py` is the reproducible final replay, recording both its own and the
verifier's hashes. It does not execute a VM or change any disk.

## Independent review corrections

`results-hardened.json` retains a fresh replay after two review findings. Every
prior main's complete validated marker must end before the named guest OPEN
request, not merely before the selected process main. Timing hooks must be main1,
launch-delegate2, window-request3, followed by active/appeared in either order at
4/5, with no duplicates. Actual67 still passes the recovered scope; all five
other actual outcomes are unchanged. Two additional parsed-copy negatives
(concurrent prior main and swapped delegate/window hooks) reject specifically at
these checks. The earlier replay remains retained rather than overwritten.

`result-output-classification.json` is a fresh actual67 replay after correcting
one output classification: the pre-OPEN PID269 main remains fully retained under
`recovery_scope.prior_main_only_records`; it is no longer mislabeled in
`post_strict_other_process_records` (empty for this attempt). No verification
condition or earlier replay changed.
