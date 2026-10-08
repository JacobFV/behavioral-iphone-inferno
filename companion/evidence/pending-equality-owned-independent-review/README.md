# Independent actual five-site owned-fixture audit

PASS of sourceec08c11bee / actual evidence5ea1073203 within firmware-free scope.
This reviewer launched no VM. The read-only script reparsed the retained raw CPU
log, checked exact site/register semantics, and matched QMP IDs/arguments/replies
and byte boundaries rather than accepting report assertions alone.

All5193 snapshots are complete; accepted-mode, equality-predicate, matching-false
and matching-true each have1038, final-return has1041. Unequal counts remain
explicit: no pairing, call count or subtraction is inferred. There are no unknown
PCs, malformed/orphan/truncated records or semantic violations. Exact owned
values are mode0, requested/bf4-token253, matching-local0/1 and statusE00002D5.
The fixture verifies these values only; it does not test production mode1/2 paths.

All nine fixed ADP events were actually queried disabled before each of three
enable attempts (27matching raw replies). One-second deadline window contains
4946 complete snapshots, early cleanup246, and lost-enable-response injection1.
Each actual enable has an empty QMP acknowledgement; each restore returns to
`guest_errors`. Untraced gaps/final tail contain guest-error output without CPU
blocks. Quit36 and host-QMP SHUTDOWN are present; recorded emulator exit0.

The fixture filter is relocated to owned code, while the mailbox response retains
the selected production filter label; both are recorded separately. Its slide
file is explicitly synthetic. No actual original-kernel reachability, iOS boot,
rendering fix, frame-completion predicate, process/thread identity, cross-site
mode attribution or same-call conjunction is established here. File offsets are
emitted-byte boundaries, not exact guest event times.
