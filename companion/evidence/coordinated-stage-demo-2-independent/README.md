# Independent actual coordinator2 review

PASS: the first complete `stage-import` run used stable baseline source and the
pinned session2. No manual mailbox control was added. `audit.py` recomputes the
raw content contract, prefix hash/offsets, command/source binding, sole finish
request/response, normal QMP shutdown and seven-file metadata/retention linkage.
No VM or metadata action was performed by this reviewer.

Actual raw plan has ImportedDemo.app / org.inferno.companion.ipademo, three entries,
71939bytes. Wrapper67392, launcher69136, imported tree71939 and cache596664
readbacks have zero mismatches. Original Applications remains root:admin0775;
new target metadata becomes root:wheel0755. FINISH0/unmount0 precedes COMPLETE.
The57593-byte prefix SHAe5e4016a9caaa2563555851c5100d4c3d19f7b9c796805e9ed4af846184b5f21
was captured before the sole coordinator `finish-observation` creation timestamp.
Raw QMP quit and host-QMP shutdown precede all seven freeze journal records.

All seven current files match their frozen identities, are0444, and their recorded
full hashes match ordinary retention. Only these new files were frozen; inherited
backing identities remain unchanged. Both runner and emulator PIDs are absent.
No INCOMPLETE/failure marker remains. Verified-stage SHA
79bbdd1c93261b347977293ab70e0756f5341dfca8bd9a17f596879b2fe1b83f
is linked to the actual report, raw content and retention hashes.

The coordinator/preservation already performed full namespace/backing reads;
this review did not repeat them. It checked their recorded hashes against one
another and actual metadata, with raw small-file hashes and byte references.
This establishes successful recovery staging, not installed app execution or a
rendering fix. The earlier failed preflight attempt remains separate and retained.
