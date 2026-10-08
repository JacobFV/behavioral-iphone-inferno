# Durable-source recovery staging: independent audit

PASS for the new durable stage, not an installed app execution claim.
`audit.py` replays the actual raw content and shutdown checks against retained
files, verifies all72 session source pins at the persistent checkout, and checks
current new-disk identities against freeze and preservation records. It performs
no VM action, chmod or duplicate full disk/backing hash pass.

Session SHA256: `faaa48f9b2f7a9f8f1b6f705e09c72a59c05c1025c7af7d355ed1a4af35ed044`.
Verified stage SHA256: `20e76bb692b788f46884914cef71c835a8dbdd24c5c0c79314c73ea4a98c9876`.
Persistent source revision: `3f8b2d5623a2ac862eba2899771049c44b197316`.

The new session binds this revision's boot/control files, including the newer
pending-equality host implementation. It does not reuse or waive session2's
older runner source pins. Raw preparation records show the exact three imported
files (71,939 bytes), wrapper/launcher/cache zero-mismatch readbacks, legitimate
Applications parent metadata, new bundle metadata preservation, result0/unmount0
and PREP_COMPLETE. The content checkpoint predates the sole finish-observation;
actual QMP quit/host shutdown and exit0 precede freezing all seven NEW files.
Ancestor identities remain unchanged; KEEP binds the new root. Runner and
emulator PIDs are absent. No incomplete/failure marker remains.

`result.json` retains raw hashes and record byte ranges, actual control/QMP
chronology, source pins and the seven-file cross-check. Disk hashes are the
coordinator's completed full-read results, cross-checked with preservation and
current metadata rather than redundantly recomputed. This point-in-time audit
is not an exclusive host lock. The guest records contain no cryptographic
session nonce; association uses the fresh run and pinned command/profile.
