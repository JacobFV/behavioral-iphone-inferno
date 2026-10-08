# Independent fixed pending-branch fixture review

Reviewed source `ced190c3fb` + `73bc914b76`, and actual retained execution
`0e240827bb`. No VM or guest action by this reviewer. The read-only audit script
reparsed the raw register dump and matched QMP IDs, payloads, acknowledgements,
file boundaries and final host-QMP shutdown against the retained transcripts.

Result: PASS within the explicitly firmware-free scope. All3261 snapshots are
complete; each of the three exact relocated PCs occurs1087times. No unknown PC,
malformed block or semantic violation. Before each of the three enable attempts,
all nine fixed ADP events were queried disabled with matching QMP replies.
Deadline, early cleanup and simulated lost-enable-response paths each restored
`guest_errors`; the raw gaps and final tail continue guest-error lines without
CPU snapshots. Final quit36 has its acknowledgement and host-QMP shutdown.

The source keeps the original two-PC baseline default, requires explicit profile
and diagnostic opt-in, and uses fixed three-PC filtering. The parser ignoresX10
at the null site, exposes active-token values only whenX11is nonzero, and rejects
inconsistent queued-token equality/null pointers as explicit semantic violations.
The prior static original-kernel/liveness review is `1ebe6759e4`; this fixture
adds mechanism coverage, not actual production-kernel execution evidence.

The raw report's mailbox response deliberately names the production filter while
the fixture command uses its relocated owned filter. Both are retained separately.
The slide file is explicitly synthetic. No iOS success, atomic guest-memory
snapshot, CPU/thread pairing, mode decoding or production-PC reachability claim
is supported by this fixture. Buffer offsets describe emitted bytes only.
