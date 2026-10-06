# Owned System-app staging: rejected copy and verified retry

Stage31 cloned the stopped stage29 root and paired auxiliary namespaces. It
staged only owned helpers and the owned two-file InfernoProbe.app under
/Applications, plus the explicit launchd configuration. Original Apple executables
and signature files were not altered by this preparation.

Actual guest readbacks in stage31 serial compare wrapper67,392 bytes,
launcher67,936, unlock helper66,944, System app72,730, and cache596,664, each with
zero mismatches. The tree comparator also checks modes, ownership, entry names,
and symlink targets. All System mounts were normally unmounted, then the helper
emitted COMPLETE. Intentional early runner termination subsequently produced an
acknowledged QMP quit and emulator exit0; attempt_completed=false reflects that
host stop, not a claimed full iOS journey.

Stage30 had failed before any full-system handoff: copying the app directory
recursively into an already-created directory nested the bundle. Readback
reported four mismatches, followed by normal unmount and helper exit62. Stage31
retried from the clean stage29 source using the existing copy_contents routine.
The rejected disk was not reused. Its raw failure section, stopped hashes and
report are retained here; provenance includes the full external serial hash.

The owned unlock helper now emits individual phase markers, allows600 seconds
for cold startup, and makes at most one normal empty-passcode attempt on the
VM's newly created no-passcode bag. Its initial state queries, single action,
and subsequent state queries precede optional Data access. The job has
KeepAlive=false. Readiness bounds only its own original ps child to600 seconds.
No runtime unlock, registration, app launch, or UIKit result is asserted here;
those require the separate boot logs.

The build manifest's HEAD precedes its final working-tree fix commit; all source
file hashes were checked against committed6ed274f6a2. Compilers, signers, original
firmware, binaries, ramdisks and disk images remain outside Git.

After the host reached99% disk usage, the stopped rejected stage30 generated disk
set was retired (about7.66GB allocated). Its exact hashes, report, raw serial and
reproducible source remain preserved; successful stage31 and its source were not
removed. The retirement record distinguishes retained evidence from discarded
reproducible disk products.

After stage33 was verified and stopped, obsolete generated preparation disk sets
24, 25, 26 and 28 were retired with explicit authorization, reclaiming
30,643,793,920 allocated bytes. Every namespace was rehashed against its stopped
manifest; reports showed emulator exit0 and acknowledged QMP quit. Open file
descriptors were checked before hashing and immediately before removal. All logs,
reports, profiles, stopped hashes and source artifacts remain available; per-set
retirement manifests record their hashes. Preparations21, 27, 29, 31, 32, 33 and
all actual boot tuples were left intact. Only these four generated disks
directories were removed.
