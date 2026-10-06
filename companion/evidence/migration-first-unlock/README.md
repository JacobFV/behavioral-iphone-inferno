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

Additional read-only attribution of the original standalone SystemAppMigrator
(UUID C04AB570-BC36-3A43-8926-DC18563A3685, matching report image59; SHA256
72d1cfef7d09c24d36990953ed0024db3c02a1a37fe8e80c472bcb4fad2a1b25)
identifies the dispatch group as `systemAppInstallGroup`. Caller+0x9b90 tests
its result and selects original log messages for successful system-app demotion
or timeout waiting for apps to demote. Thus the 10-minute pre-failure report is
waiting for demotion completion. Linking that timeout to the later Returned NO
is plausible but not established by a captured numeric error; the failure
snapshot itself has no plugin user frames. No demotion or migration code changed.

Boot7's bounded owned diagnostic subsequently observed first-unlock0 before and
after exactly one MKBUnlockDevice(NULL,NULL), which returned-2. The adjacent
original AppleSEPKeyStore log reports selector9/e00002e2. Data X_OK remained
EPERM. Raw state0 is not labeled unlocked: the original extended-state decoder
can map missing fields from malformed nonempty DER to zero; the separate
first-unlock bit query is the meaningful observation here.

Read-only tracing of the original kernel identifies the default-bag selector9
gate as client flagbit4, set only by Boolean `com.apple.keystore.device` in the
calling process's entitlements. Without it the driver returns NotPermitted
before secret conversion or SEP unlock. Original keybagd and SpringBoard also
carry this entitlement. The controlled follow-up declares only that key on our
owned ad-hoc helper. Its compiled object is byte-identical to the prior build;
no Apple executable, signature identity, or simulator protocol is changed.
The accompanying boot7 excerpt is a live serial snapshot, not a completed-boot
claim. Follow-up execution results are deliberately not asserted here.
