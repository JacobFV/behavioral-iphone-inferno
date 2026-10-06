# Owned app event relay

The app writes only its own six fixed marker kinds to
`/var/mobile/Library/Caches/org.inferno.companion.probe.events`. It opens without
following symlinks, verifies a regular single-link uid501 file before truncating,
and sets mode0600. At most64 records/16KiB are written. Write or identity failure
disables the file route; existing NSLog/stderr markers remain.

A fresh exec child of the existing readiness observer polls only that path,
checks ownership/type/size, accepts only exact record grammar and allowlisted
markers, and deduplicates PID/sequence pairs. It runs at most7200seconds and emits
at most512 records across32 app PIDs. It does not respawn, write, execute input,
post notifications, or require additional entitlements.

Both sides independently query `kern.bootsessionuuid`; malformed, zero, absent,
or foreign boot identity fails closed. Apple XNU xnu-7195.81.3
`bsd/kern/kern_sysctl.c` lines2612–2614 declares this read-only SYSCTL_STRING;
the original supplied kernel contains this exact name. Actual guest support and
file access still require execution evidence. This avoids accepting an earlier
boot's file even when the copied disk retains it or the clock changes.

ABI declarations are narrow self-authored Darwin LP64 declarations (stat144bytes,
64-bit off_t, mode_t16bits, sysctl size_t64bits). The record header is shared by
writer and reader. A host ASan/UBSan harness exercised foreign uid/boot rejection,
unknown/overflow fields, accepted main/tap records and duplicate suppression.
This is parser validation, not guest file-I/O evidence or an app journey.

The container-aware revision resolves the writer's cache directory through original
NSFileManager (NSCachesDirectory13/NSUserDomainMask1), rejecting the mobile-home
fallback. The reader resolves only LSApplicationProxy for
`org.inferno.companion.probe`, verifies its installed bundle URL, and uses the
original dataContainerURL plus the fixed Library/Caches basename. Missing data
container reports a failure and retries lookup every30seconds; it does not create
one or search other apps. Container provisioning is a separate original install
operation and is not asserted by these path changes. No sandbox grant is added.

Actual boot29 writer displayed READY after original cache resolution while LS
reported nil dataContainerURL. Thus nil registration metadata did not mean the
app lacked a writable home. The reader now falls back only to original
MCMAppDataContainer lookup for the exact owned identifier, with
createIfNecessary=NO, then reads its returned URL. It never creates a container.
The installed original framework's inherited method has ABI
NSString*,BOOL,BOOL*,NSError** and returns an autoreleased object; its url method
returns the manager-owned location. Authorization success remains an execution
question and bounded error codes are logged without adding grants.
