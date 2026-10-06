# Inferno companion execution record

## 2026-10-06: real t8030 initialization and early-boot preparation

**Executed milestone:** the simulated-SEP rebuild at source 877b07069a completed,
passed the firmware-free QMP smoke, then executed a bounded 120-second recovery
boot. Raw serial shows `BSD root: md0`, launchd's `Early boot complete`,
`restored_external` running, USB enabled and `waiting for host to trigger start
of restore`. QMP shutdown returned exit 0. Root independently inspected the logs
and the captured 828x1792 framebuffer: Apple logo and an empty progress bar.
This proves kernel and recovery-userland execution with a real framebuffer;
it does not establish installed iOS/SpringBoard boot, touch interaction or an app
journey. Committed raw evidence and reviewed summary are under
`companion/evidence/recovery-ramdisk*`; full local report/disks are under
`.local-build/reports/simulated-sep-boot-1/`.

The complete official IPSW download and local profile preparation also completed.
Archive SHA256: `706742ed60327a5247c29ccc5bf7e6ce9bbf11dd30a468f8f6fc9da76bdca96d`.
`companion/run prepare` extracted all four components from the complete local
archive, verified their SHA384 against BuildManifest, and produced the same SHA256
values as the early HTTP-range extraction. The durable profile is
`/home/brandonin/.local/share/inferno/images/ios14b5/verified-profile/profile.json`.

Read current upstream setup documentation and the pinned t8030 source. Upstream's
documented example is iPhone12,1 / n104ap, iOS 14.0 beta 5 build 18A5351d; current
upstream lists 14.x as supported, with later versions still upcoming. Its full
restore instructions forge tickets and use real SEP firmware. This work instead
tests the existing direct-kernel, simulated-SEP recovery path under our rule
against signature forgery. This is an experiment, not proven full restore support.

Apple's public 5,507,405,643-byte IPSW was acquired outside Git at
`/home/brandonin/.local/share/inferno/images/ios14b5/`. HTTP range extraction with
ZIP CRC checking supplied the four initial inputs without waiting for the full
download. BuildManifest confirms n104ap research erase build 18A5351d. Their
absolute paths, SHA256 and official Apple URL are in `range-inputs/profile.json`.
No SEP ROM, SEP firmware, device keys or forged tickets were acquired/created.

The first actual t8030 run, using original binary SHA256
`26443d17c93b2e9957a3ab745bbe2ba39f3b4708a07316b55c3ebefc36f14d8d`, decoded the
kernel and applied upstream's in-memory kernel patches, then failed with
`Simulated SEP cannot be used with data encryption at the moment.` Serial output
was empty. Root inspected the actual stderr and source guard; no guest execution
is established by this attempt. Raw logs, QMP transcript, argv and inputs are at
`.local-build/reports/first-t8030-boot/`.

Commit 877b07069a adds an explicit `--simulated-sep` build option and a two-line
guard around upstream's hard-coded data-encryption switch. It selects existing
simulated-SEP/unencrypted-device-tree code; default builds retain upstream behavior.
The original binary/manifest are retained in `.local-build/binaries/emulated-sep/`.
Subsequent runs use the rebuilt variant. Companion boot/preparation tools
are documented in companion/BOOT.md; all runtime assets remain outside Git.

## 2026-10-05: user-directed pivot

The user requested wrapping ../behavioral-iphone and creating this companion fork.
Upstream cc4302a99167abec69b714cfd00c38caece7e7de is checked out with complete
commit ancestry (partial clone fetches historical blobs on demand), remote upstream,
and local branch companion/linux-runner. No GitHub-hosted fork was created.

The prior effort's source, pending branches, tracked patches and selected evidence
are preserved there; ../behavioral-iphone-handoff.bundle backs up its Git refs.
Its framework workers and demo server were stopped. The prior project remains
unfinished; no phase-completion claim accompanies the pivot.

Current host reports aarch64 Linux. glib2.80 and pixman0.42 are available; several
build dependencies and Meson/Ninja were absent. Local dependency/bootstrap build
work subsequently completed, as recorded below. No firmware has been downloaded, no iOS boot performed and no
application run on this backend yet.

## First executable checkpoint

Build succeeded at committed fork revision a63bb71bac. The pinned upstream base
is unchanged; the one upstream build change explicitly links liblzfse for the
Apple SoC code, whose boot.c already calls lzfse_decode_buffer. Its dependency
was previously supplied only by the optional DMG module. The minimal build also
needs explicit PNG support. No runtime behavior or Apple firmware was patched
by this companion work.

Root independently ran companion/smoke.py against the built binary. QMP greeting,
capability negotiation, version/machine/status/CPU queries and graceful shutdown
passed. The real executable advertises t8030; this none-machine run had zero guest
CPUs and no running guest. It establishes executable/control-plane operation,
not iOS boot, app launch, graphics compatibility or runner economics.

Committed evidence: companion/evidence/initial-build.json and
companion/evidence/initial-qmp-smoke.json. Their binary SHA256 values match.
Raw build output and stderr remain in .local-build/build.log and
.local-build/reports/initial-qmp-smoke/. Dependencies, the source checkout,
branding resources and binary are local and ignored by Git; retain the build
root together rather than distributing only the executable.

Next milestone: prepare a documented, authorized iOS image profile outside Git
and establish real boot/display/input, then run one owned app. No firmware was
downloaded and no native/simulator parity claim is made. Current bootstrap is
Ubuntu24.04 ARM64 only; other runner architectures need their own dependency lock.

## Session handoff readiness

`companion/run` now provides status, check, build and version commands independent
of the invoking working directory. NEXT_SESSION.md contains the concrete next
boot/app tasks, source facts and persistent user preferences. The root README and
AGENTS.md both point to it.

The independent readiness audit found no Git alternates, no /tmp-target symlinks
in .local-build and no unresolved executable libraries. Optional trace metadata
was generated; future builds generate it automatically. Build PATH is normalized
to the local tool venv and system binaries. Dependencies remain local and durable.

A fresh actual check passed with an empty inherited environment except PATH and
locale: `env -i PATH=/usr/bin:/bin LC_ALL=C.UTF-8 ./companion/run check`.
Evidence: `.local-build/reports/session-handoff-smoke/report.json`.
`./companion/run status` confirms the binary matches the saved build manifest and
that the most recent matching QMP execution passed. No heavy rebuild was needed
for these launcher/documentation additions. No iOS boot/app claims have changed.

Setup work is intentionally handed off so the user can close the old session and
open a new session rooted here. There are no continuing framework workers or
emulator processes from this setup. Continue with NEXT_SESSION.md in the new one.
