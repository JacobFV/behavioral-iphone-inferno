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

Actual boot30 MCM lookup returned error55 (not entitled), while the app's own
writer remained READY. The next reader uses original libproc metadata instead,
without any new grant: UID501 PID enumeration capped512, exact executable path
and SHORTBSDINFO UID check, at most4 matching processes/128 FDs each, vnode-only
FD metadata, exact event basename/uid501/regular/single-link/16KiB bound. It
rechecks process identity and requires the opened file's device+inode to equal
the original FD metadata before reading. MAC checks remain active; their actual
return and errno are recorded, not bypassed. It reads no process environment or
other file contents. The app footer separately displays its actual cache path.

Actual boot31 process metadata located the exact owned file, but the reader's
normal open returned EPERM. No filesystem or manager grant is added. The next
transport is TCP bound only to guest127.0.0.1:37373, with no host listener or
forwarding. App markers generate the same bounded boot/PID/sequence/event/count
record and send it over one short connection, while retaining the local journal.
Nonblocking connect/send/receive use at most8 attempts with250ms polls per phase;
SO_NOSIGPIPE prevents disconnected receivers terminating the app. The receiver
accepts at most64 connections in7200seconds, one line under192bytes each, and
validates the same strict grammar/boot/sequence limits. It checks the claimed PID
against original executable-path/uid APIs; this is explicitly NOT peer-PID
authentication. It never relays unvalidated payload text or changes UI input.
Footer NET=0 means bytes sent, not receiver acceptance. Actual serial records and
reviewed app frames/tap response are still required for journey completion.
