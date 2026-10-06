# Inferno companion execution record

## 2026-10-06: real t8030 initialization and early-boot preparation

### Further executed checkpoints

- **Current full-system boundary:** original guest IOKit initialized the disposable
  VM effaceable namespace; original MKBCreateSystem returned0 and wrote the system
  keybag. Direct-root-6 retained all auxiliary namespaces, passed keybag/mount/FIPS,
  and reached launchd “Early boot complete. Continuing system boot.” It stayed
  alive for180seconds with no observed panic, but the actual framebuffer remained
  Inferno branding. SpringBoard and owned UIKit execution remain unestablished.
  Raw evidence: `companion/evidence/keybag-initialization*` and
  `companion/evidence/direct-root-early-boot*`. App staging independently verified
  all four owned files and clean unmounts in app-staging-1; app and process-observer
  boots are now running. Continue diagnosing UI readiness, not a checkpoint pause.
- **Software-rendering compatibility applied:** pinned upstream InfernoFSPatcher
  produced45 records changing180 cache bytes. Original and patched full2GiB
  SHA256 values both matched in the guest, with original fsync and normal System
  unmount. `companion/fs-patches/` reproduces the guarded plan and execution;
  Apple cache bytes and patch payload remain outside Git. Raw execution evidence:
  `companion/evidence/software-renderer-preparation*`.
- **Owned launch jobs integrated:** loose jobs yielded no markers in app-boot-1
  over240seconds. Original launchd uses a consolidated configuration. Stage23
  preserved432 existing entries and added only our app and process observer,
  with596523-byte guest readback and zero mismatches. The original loader's
  explicit `launchd_unsecure_cache=1` mode accepts this edited configuration;
  no signature was generated or changed. App-boot-2 has logged “Using unsecure
  cache” and is running with periodic frames, USB diagnostics and strict journey
  checks. App/UI success remains pending actual execution evidence.
- **Data is guest-verified:** full recursive read-only comparison passed all
  13,025 files (269,210,433 bytes), modes/owners and symlink; 16,665 total entries
  including root, zero mismatches. Both volumes unmounted cleanly. The host
  7-Zip extraction failure was a reader limitation, so no Data recopy occurred.
  Raw evidence: `companion/evidence/data-guest-verification*`. An identical first
  attempt failed before launchd in framebuffer initialization; that transient
  boot failure is retained in disk-preparation-16 and remains a reliability issue.
- **Prepared disk expanded:** original APFS API enlarged the prepared container
  inside a 32GiB GPT disk with about25GiB available. Guest and host file checks
  preserved System files, gigalocker and original SEP payload; clean unmount and
  QMP exit were observed. Raw evidence: `companion/evidence/prepared-container-growth*`.
- **Owned UIKit fixture built:** `companion/app-probe/` builds an ARM64 counter
  app using self-authored declarations and LLVM ad-hoc signing. It has not run in
  the guest. The opt-in runner `--probe-journey` requires appearance/tap markers
  and before/after screenshots; actual app execution of that flow is pending.

- **Recovery USB works:** source7e70337967 fixes remote USB's synchronous BQL
  release and preserves EHCI address/status completion ordering. Actual Linux
  KVM + iOS TCG run8 enumerated `05ac:12a8`; usbmuxd connected to the device.
  The original libimobiledevice restored API queried `com.apple.mobile.restored`,
  protocol15. Clean iOS shutdown removed the device; the same Linux VM then
  enumerated a fresh iOS process as device003. Root independently repeated lsusb,
  idevice_id and the read-only service query over loopback SSH. Raw evidence and
  exact binary/source identities: `companion/evidence/usb-recovery*`. This is a
  recovery service connection, not a restore transaction or installed iOS boot.
  Reconnected recovery later hit its 120-second idle restore timeout and panicked
  during shutdown; the 300-second observation did not complete. Linux shut down
  cleanly. This later failure does not replace the independently observed queries.

- **Owned native code:** an SDK-free ARM64 Mach-O, linked against a self-authored
  libSystem declaration and ad-hoc signed only as our own code, executed from a
  cloned recovery ramdisk. Root read its marker in actual serial output:
  `INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls`.
  `companion/native-probe/` contains source/preparation; raw evidence is
  `companion/evidence/owned-native-probe*`. This is native recovery execution,
  not a UIKit app or interactive app journey. Initial LC_MAIN without libSystem
  and UNIXTHREAD experiments failed; their local logs are retained.
- **Official System disk:** decoded the unencrypted OS UDIF, preserved its APFS
  payload and wrapped it in valid 4096-sector GPT for Inferno NVMe. Direct boot
  mounted the actual System volume and ran the full-system Darwin Bootstrapper.
  It panicked at `mount-phase-1` (exit66): missing auxiliary volumes and the
  preboot firmware path. This is not installed iOS boot completion. Raw evidence
  is `companion/evidence/direct-root-first*`; preparation is documented under
  `companion/os-image/`. The source volume is unencrypted System only, no Data.
- **Linux USB companion:** official ARM64 Ubuntu booted headlessly; after
  diagnosing a 1GiB TCG setup bottleneck, resumed a copied working disk with
  4GiB and private QMP/loopback SSH. Actual usbmuxd/libimobiledevice installation
  and daemon operation were observed. First joint attachment crashed Linux in
  `ehci_irq` with an external abort and QEMU's re-entrant MMIO warning. Source
  trace points to the synchronous remote USB handler releasing BQL while EHCI
  MMIO remains active. A single-vCPU EHCI retry failed the same way. xHCI avoids that panic but
  cannot enumerate through this custom transport's control path. A focused
  asynchronous transport fix is in progress. Linux KVM separately booted with
  `query-kvm` reporting enabled; this establishes no iOS KVM capability. An earlier `guest_ready=true` report does not override this raw panic.
  Logs are outside Git under `/home/brandonin/.local/share/inferno/usb/run3/` and
  `.local-build/reports/recovery-usb-1/`.

- **Guest disk preparation:** run6 created Preboot and copied the original
  firmware tree; independent reader comparison found all 19 files byte-identical.
  Direct-root-2 still failed mount-phase-1 because missing xART aborted fstab
  construction. Original newfs_apfs checks its parent's xART entitlement. An
  explicit entitlement on our own ad-hoc-signed helper resolved its exit77:
  run8 created Preboot, xART and Hardware, copied firmware and cleanly unmounted
  both mounted volumes. Root inspected the raw serial commands, statuses and
  completion marker. Logs: `.local-build/reports/disk-preparation-8/`.
  Direct-root-3 mounted xART and Preboot and passed mount-phase-1. It then
  panicked during data-protection (exit2): missing gigalocker storage. The
  original guest initialization utility subsequently succeeded in run12: original
  `seputil --gigalocker-init` returned0 and xART cleanly unmounted. The separate
  shutdown utility hung in runs9/10; run12 used sync and normal unmount.
  Raw evidence: `companion/evidence/gigalocker-preparation*`. Data/Update creation and
  original var seeding completed in run13, with clean unmounts and 260,640,768
  bytes still available. Hardware factorydata paths were also prepared. Raw
  evidence: `companion/evidence/data-preparation*`. Independent root extraction
  subsequently found 12,465 copied compressed files read as zero bytes despite
  matching path inventories; guest reads must resolve reader limitations versus
  a real copy fault. Data content validation has NOT passed. Earlier committed raw
  evidence: `companion/evidence/apfs-role-preparation*` and
  `companion/evidence/direct-root-prepared*`.
- **Reproduced OS conversion:** root ran both committed OS utilities; full raw
  image, APFS payload and 4096-sector wrapper hashes match the original conversion.
  Logs: `.local-build/research/os-reproduced.log` and
  `.local-build/research/os-wrapper-reproduced.log`.

Continuing work uses disposable disk copies and guest utilities to populate the
missing APFS roles and preboot firmware path. The original DT supplies a zero
boot-manifest hash when no ticket is provided; creating its matching directory
does not create a signature. No Apple ticket/signature fabrication was performed.

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
