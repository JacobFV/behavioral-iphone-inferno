# Explicit original-tool stack sampling

The owned HID helper remains the sole console reader. No sample runs at startup.
The fixed line is `INFERNO_SAMPLE_V1 <32 lowercase hex ID> <current boot UUID> <SPRINGBOARD|BACKBOARDD>` followed by newline. Its READY line advertises this capability; an old helper cannot accept the command. At most two valid accepted attempts per lifetime are consumed before target resolution. IDs share the 42-entry HID/OPEN/SAMPLE replay registry. OPEN and SAMPLE cannot overlap, and gestures are rejected while either child exists.

Only `/System/Library/CoreServices/SpringBoard.app/SpringBoard` or `/usr/libexec/backboardd`, UID 501, can match. Original libproc calls must identify exactly one target and return the full 56-byte kernel incarnation structure. The helper records and revalidates uniqueid/idversion, executable and UID immediately before spawn and after completion. No caller PID, path, argv, process signal or grant is accepted.

The existing root helper executes the unchanged original `/usr/sbin/spindump` with a numeric validated target and exactly `2 100 -onlyTarget -noBinary -noFile -stdout -noSymbolicate -timelimit 20`. Original usage/parser evidence is in `companion/evidence/original-spindump-inspection/`. Original tool privileges are neither copied nor expanded. Run49 actually executed both targets successfully: twenty stackshots each, original
tool exit0, complete output and unchanged target incarnation. Kernel/kext symbol
owners were unavailable; user stacks had usable UUID/base metadata. Stackshots disturb scheduling and are not latency measurements.

The child closes console input and merges stdout/stderr into a pipe. The parent drains nonblocking reads in its existing loop. Each `INFERNO_SAMPLE_DATA` record carries request ID, byte offset, byte count and hex of at most 256 original bytes. Retention is capped at 256 KiB. A consumer must require contiguous offsets, decoded lengths, chunk count and final byte count, and retain the final completion flags. Mixed stdout/stderr reflects pipe write ordering, not separate streams. Console output errors or a missing/truncated END record cannot establish completeness.

The 60-second watchdog uses **guest** `mach_absolute_time`, not host time. Polling and console writes are cooperative and scheduling can delay them. Original `-timelimit 20` is an additional original-tool limit whose actual behavior is not yet tested. On timeout, output cap, or read/output failure, only the still-unreaped tool child is killed, after `waitpid(WNOHANG)==0` confirms ownership. Reaping is polled; an unreaped child keeps further control commands blocked. Cleanup waits at most 50 requested 100 ms intervals. Target processes are never signalled.

`complete=1` requires exit status zero, EOF, no cap/read/output/timeout error and a matching post-sample target incarnation. The tool still accepts a numeric PID internally: these checks do not atomically prevent PID reuse within the original tool. A complete transport does not by itself prove useful stacks; inspect original output and its errors. No system notification, state override, display patch, or automatic retry is introduced.
