# Stage36: original Multitouch payload, unsigned IMG4 packaging

Source is stopped app-boot-15 root SHA256
8cf8592076adef4f9daa20ff6520cc2bf157c81009561fc58041e07e91c24182
and its paired six auxiliary namespaces. This preserves the actual boot15 state
whose registry showed AppleHIDTransportBootloaderHBPP without a protocol child.

Only Preboot/<96-zero boot-manifest hash>/usr/standalone/firmware/FUD/Multitouch.img4
was added. The exact normal directory and original FUD IMG4 loader requirements
are traced in `companion/native-probe/firmware-loader-audit`. The existing guest
helper, launchd cache/jobs, app, launcher, and observer were not replaced.

The new file is an explicitly unsigned IMG4 container: outer SEQUENCE, IA5String
IMG4, and unchanged original Firmware/N104_Multitouch.im4p. No manifest, ticket,
certificate or signature was generated. The recovered 583,079-byte IM4P exactly
matches the original IPSW member; source SHA256
c0e09a061970a19dc827ad19d769c2847073df81ed293c297bc75e6569fe8e68.
Container SHA256 is
871a03fb79413e696d3bf952991ac46552a4007585c85f18cb6abbcdbf4943a2.
All firmware implementation bytes remain outside Git.

Actual recovery serial verifies **583,090 bytes, zero mismatches**, using the
existing byte/mode/ownership comparison. Original Preboot unmount finishes with
zero mounted APFS volumes, followed by STAGED and PREP_COMPLETE. The bounded
runner was intentionally interrupted after completion; its finally block sent
QMP quit id6, acknowledged, and the emulator exited0. The runner's own
`attempt_completed:false` reflects this early intentional stop, not a completed
full-duration boot. Raw report and transcript preserve that distinction.

All seven stopped namespace hashes are recorded. Final root SHA256:
6a7dba55d2e16890eec2a76d980a10016cdde0ad2265387048cd76ee699db1ac.
The archived recovery emulator was used explicitly; no emulator or validation
changes were made for staging. This proves packaging and disk placement only.
The next full-system boot must establish actual original-loader acceptance,
firmware download, protocol creation and touch handling separately.
