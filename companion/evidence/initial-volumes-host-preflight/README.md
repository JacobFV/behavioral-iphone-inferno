# Initial-volume coordinator: host-only preparation checks

No recovery/installed VM has run for this coordinator. Source review and an
allocated actual recovery attempt remain required before any phase-success claim.

Actual input availability: both historical original System-only8GiB wrappers
existed but were mode0664. Neither was chmodded. Parent explicitly authorized a
NEW sparse/reflink-auto copy under `images/ios14b5/initial-volumes-source-1`.
The actual copy command and before/after identities are in copy.json; original,
new and post-copy original full hashes matched93f97d...32594. Only the new copy
was fsynced/frozen0444; its KEEP marker retains the backing dependency.
Copy record SHA256e409966ed0abfd20d19168e7d3fab2116df4c076d26c3bd9b69092dc4b01d071.

`preflight.py` executed validate_inputs against actual pinned profile, reproduced
raw/helper, original wrapper record, new immutable root, emulator and tools.
It passed, including the actual new-root full hash. `host-preflight.json` retains
that invocation's source snapshot at6c2a69bf9f. Later coordinator-main hardening
changes source hashes; this check does not claim to execute those later paths.
The retained historical preparation8 raw log is deliberately rejected because
its older BEGIN/COMPLETE ABI does not match the new exact gate. It is historical
support for the underlying role operation, not a falsely promoted new run.

After timeout-cleanup hardening, one actual firmware-free owned host subprocess
spawned a sleeping child. The command deadline expired; the private group was
stopped, child was absent, and remaining-session-members was empty. cleanup.json
retains actual argv/stdout/stderr hashes and cleanup result. This is not VM or
guest evidence. Final serial-prefix and metadata stability checks remain to be
exercised in an actual separately authorized role-only recovery run.
