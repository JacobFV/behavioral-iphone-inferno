# Baseline migration failure and first-unlock wait

The stopped 1800-second app-boot-3 snapshot was cloned into a read-only recovery
inspection. The serial log retains six complete .ips exports, byte counts and
FNV1a64; extraction validated every count/checksum. Normal Data unmount and guest
completion precede acknowledged QMP quit and emulator exit0. The host runner
was intentionally stopped after observation, so attempt_completed is false.

The 02:25:58 report explicitly says SystemAppMigrator returned NO. Moving on to
MobileSlideShow therefore does not establish successful SystemAppMigrator
completion. Its prior 02:17:34 wrapper thread1324 waits in dispatch_group_wait
at standalone plugin image59+0x6374, called from image59+0x9b90. The failure
snapshot contains no wrapper user frames; installd is draining an NSError on
an XPC queue. These stacks alone do not identify the underlying error value.

At 02:36:14, assetsd384 thread4233 is waiting in
+[PLFirstUnlockProtection waitUntilFirstUnlock]. Its migration thread4234 waits
for the library-state operation. Plugin wrapper377 thread4159 synchronously
waits in PLAssetsdMigrationClient cleanupModelForDataMigrationForRestoreType;
datamigrator111 thread1207 waits for that wrapper. This is a concrete first-unlock
wait, distinct from the earlier active LaunchServices plist seeding snapshot.
It does not by itself prove which keybag state or notification is missing.

The original cache UUID matches image2 of the reports. Symbolization uses the
original, unchanged cache's nearest symbols and preserves offsets. Apple
standalone image frames are not guessed. This directory contains observed VM
logs/reports and symbol names, not Apple implementation binaries or key bytes.
