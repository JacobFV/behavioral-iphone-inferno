# Continue active Inferno companion work

Workspace: `/home/brandonin/Documents/behavioral-iphone-inferno`.
Read AGENTS.md, companion/README.md, PROGRESS.md and companion/OWNED_JOURNEY.md.
This is the Inferno pivot; never resume the archived framework implementation.
The user explicitly wants continuous work across status questions and intermediate
milestones. No pause or handoff requested. Parallel workers are authorized for
independent work in isolated worktrees; commit progressively.

## Current execution, 2026-10-06 13:10 local

No VM is live. All through43 stopped. Active task: investigate the intermittent
real display freeze in41 while finishing a reproducible installed-iOS runner.
Do not treat a healthy comparison as a fix.

- 41: real tap1 but VNC and QMP remain counter0, including continuous30-second
  observations. Ordinary F6 Home and one OPEN produced real background/foreground
  callbacks in the same process but no visible redraw. No second counter tap.
  Strict after-capture deliberately withheld. Root SIGINT2 to runner, normal QMP
  cleanup/emulator0, attempt failed. Tracked verifier rejects it. All7 disks and
  ancestors retained; root manifest explicitly `forensic_only:true`, rejected as
  a future overlay base. Evidence `display-staleness-41*` and
  `owned-display-stale-forensic-41*`. No app-mainloop permanent block or VNC-only
  cache explanation fits the observed callbacks/shared stale QMP pixels.
- 42: unchanged baseline emulator/frozen50 guest bits. Fully tracked strict0→1,
  one ordinary Home/reopen retaining1, normal stop, verifier and disk checks pass.
  Nine fixed display-register snapshots are healthy reference only. Evidence
  `tracked-workflow-42-visual`, `display-registers-42-actual`,
  `owned-tracked-controls-stopped-42*`.
- 43: diagnostic-only emulator source0132ad93ca, SHA
  1e369a50d11a417a50d8a05d9bc8dad7ebd443ca4d9b2db0b71271e55139a6b7.
  Same frozen50 guest bits, TCG. Root reviewed counter0→single tap→1 in VNC and
  both strict QMP captures. Tracked verifier passes. Normal finish-run/emulator0,
  all7/ancestors preserved. RootSHA
  6c7e0faf7bc72db50c1bea53c4f1e79962d2fb2a2fc13525ca202033f3d36b63.
  Boot28E7DE2C-2059-488B-8290-F2BD07870CFA, PID218/main1912722120.
  Counter requestfd6aa9d92d38431e8a91b65ba8a9a4af.
  QMPbefore08d4e0485d4b4fc84905aee3d535bf8df5dbec7c2f8e1b1425fb205947624fde,
  after190911dc8e8ee21b4ad180aa4934eb4fe95d933cd51f6f223a2315448168332d.
  Trace enabled before beta Close for60seconds; actual deadline disabled all5.
  Evidence7f983d247d/`display-trace-43-visual`,93b6d271c2/
  `owned-display-trace-stopped-43*`. Native worker auditing complete raw trace.

Actual43 exposed a TELEMETRY LABEL DEFECT: original genpipe.index is never set,
so both pipes print0. Source draw-call order and controls distinguish the healthy
first drawn/second disabled pipe, but index alone cannot. Native worker owns tiny
followup passing explicit0/1 solely to tracecalls, leaving migrated state and
emulation behavior unchanged. Build only after root review/merge. Bootworker is
archiving43 diagnostic binary before replacement. No44 launch authorized yet.
Disk worker owns optional host log byte checkpoints in owned-control.py to help
bracket file-visible trace records; trace log backend has no timestamps. Such
checkpoints do not prove device-event times because logging can buffer writes.

## Trace and control workflow

Root owns ALL live guest input, VNC, Home, OPEN, register queries and finish-run.
Bootworker owns launch/lifecycle/postflight, with explicit root launch instruction.
One VM during this investigation. Headless Unix endpoints only; no user windows.
The runner is sole QMP owner; never open a second raw QMP connection to a guest.

Use tracked commands in companion/OWNED_JOURNEY.md:

- `companion/run owned-control --report REPORT --output NEW swipe 16384 32270 16384 9145 --duration-ms 1500`
- Lock may need a second swipe only after actual reviewed state/first completion.
- Reviewed beta Close: `tap 16384 18560 --duration-ms 150`.
- Reviewed counter: `tap 16384 20316 --duration-ms 150`, exactly once.
- `companion/run observe --socket CURRENT_UNIX --output NEW --settle-seconds 4`.
- Continuous capture: `observe ... --observe-seconds 20` (no input allowed).
- Home: `observe ... --home-button` (fixed F6→SMC Menu press/release).
- `companion/run control --report REPORT probe-capture-before`, only reviewed0.
- `... probe-capture-after`, only genuine tap1 AND reviewed1.
- `... probe-status` gives live state; live report.json is initial/stale.
- With keepalive, `... finish-run` after strict completion requests normal cleanup.
- `... query-display-registers`:18 fixed audited nonconsuming MMIO reads, sequential
  not atomic, no framebuffer DMA/arbitrary addresses.
- `... trace-display-window --arguments '{"seconds":60}'`:5 fixed events,
  integer1..60, no overlap, cooperative deadline via sole mailbox poll and cleanup.
  Journal display-trace-control.jsonl records actual results. Trace can affect timing.

Never use guest ACK or lifecycle JSON as visible success. Retain actual raw logs,
image hashes, source revisions and direct image review. QMP828×1792 vs VNC832×1792
includes padding. Convert PPM losslessly to PNG for view_image and check decoded
RGB equality. A failed first tap must not be hidden by a second tap or aftercapture.

Poststop:
`companion/run verify-journey --report REPORT --output NEW.json`
`companion/run preserve-stopped --report REPORT --output REPORT/stopped-disk-hashes.json`
Default preservation requires normal completed run. Explicit `--failed-attempt`
retains error/strict state and marks root forensic-only, while still requiring
emulator0, actual QMP shutdown, seven disks and ancestor checks. /proc descriptor
checks are scoped to readable processes; permission gaps are recorded.
Verifier checks raw markers/input/QMP/PPM hashes, not image semantics. Without an
independent arrival observer, chronology uses reviewed capture-gate source hash.

## Current immutable guest tuple

Four owned artifacts, unchanged in37–43:

- App22 `~/.local/share/inferno/app-probe/exec-build-22/InfernoProbe.app/InfernoProbe`,
  74976bytes SHA d05f1b32523684a5c89d41cb2c35fbf0207b62adf864c27fab4d5973bf8e6176.
- Launcher22 same directory `inferno-launcher-open-error`,69264bytes,
  SHA0f6626102deedabe4f5c93dafbd3c757387836c463d6b59bf3204932e550bf17.
- Reader54 `~/.local/share/inferno/native-probe/helper-build-54/inferno-readiness`,
  86448bytes SHA2440b210892898f43bd2f2afe3907ee5b682262d1d71c47e8c940757aa46c0b2.
- HID54 same directory `inferno-hid-input`,70848bytes,
  SHAf670cb9ec09933514326df8f6cb4995883b22d58852b12d7511ae075cec06943.

All172 imports checked against original cache; Info/jobs unchanged. Exact HID grants:
com.apple.developer.hid.virtual.device=true and
com.apple.security.iokit-user-client-class=[IOHIDResourceDeviceUserClient].
Owned bundleorg.inferno.companion.probe, /Applications/InfernoProbe.app;
launcher/usr/bin/inferno-launcher. Preserve original LS System classification only
for that owned path and NSObject isa ABI fix. No signer/trust metadata changes.

Baseline emulator through42: source1cebf0c00be038e7156d82578214c2cafa109873,
SHAe3da84b179ce328e06a0f917aabb8e4d80c8a4cf64701212464831a270e1741e.
Archived read-only `.local-build/binaries/simulated-sep-first-unlock-e3da84b179ce/`.
Current binary described above43; build command retains configuration:
`companion/run build --simulated-sep --enable-kvm` (8 jobs).
KVM compile capability does NOT mean guest native/KVM execution; iOS uses TCG2CPU/
4GiB, simulatedSEP, upstream direct-kernel patches and software rendering.
Profile `~/.local/share/inferno/images/ios14b5/verified-profile/profile.json`.
Recovery archive `.local-build/binaries/simulated-sep-7e7033796707/`.

## Backing chain: keep exact paths and every dependency

All under `.local-build/reports/`,0444+KEEP. Max4 qcow layers:
37–43 layer4 → stage50 layer3 → stage44 layer2 → boot27 layer1 → stage43raw.

- disk-preparation-43/disks/root.raw,34359738368logicalbytes,
  SHA69e8378c71d1f29840baa7ae16811d3f6285bf27042501a79e8139f8a5ad61d5.
- app-boot-27/disks/root.qcow2,140443648bytes,
  SHA6898ad82af6bfb96168d2b7dd8febcfa977ef703679739197a40a08d735b6d4c.
- disk-preparation-44/disks/root.qcow2,3145728bytes,
  SHAa26c50b4f51e5bb8a7c67889e2078649324851849f826f0eb754680f91f66f5d.
- disk-preparation-50/disks/root.qcow2,3604480bytes,
  SHA3745a6abe402cd6b645a29a7fd5a9853b7ac06e9c8e3ca6bfa9099f21db5a693.

Stage50 intentionally stopped recovery with Signal15 after verified staging,
reporterror/attempt_completed:false. Do NOT blanket-reject report errors and break
this established backing tuple; forensic_only rejects failed app attempts.
Future staging must branch44 and replace ALL components changed from44. Never
stage50 and boot another layer5. Loader verifies actual qemu-img headers, hashes,
paired auxiliary6copies and descriptors; postflight rehashes ancestors.
Keep stages45–49 and other actual used dependencies too. No retirement authorized.
Dependencies/binaries/disks/credentials outside Git. Never copy Apple binaries
into trackedtree, decrypt FairPlay, extract keys, forge signatures or impersonate iCloud.

## Completed measurements and limits

37/38: strict0→1 and three warm Home/reopen cycles each, same kernel process
identity and counter1. Warm OPEN→active747.806/709.095/735.643ms in37;
721.110/765.458/702.043ms in38. Guest lifecycle intervals, not presentation/native.
38 additionally ordinary app-switcher dismissal, original ps absence snapshot
BEFORE OPEN, newPID492/unique492/idversion1414/main33927344147 and reviewed0.
Request→active884.627917ms; caches uncontrolled. No forced kill/cache-cold claim.

39/40: actual concurrent strict journeys, both reviewed1 after a common60-second
foreground-idle sample; normal stops/all7/ancestors. 61CPU/13smaps rounds,
38.74CPU-seconds,64.566591%onehostcore, peakPSSsum11,558,389,760bytes,
peakRSSsum11,580,973,056bytes. No VNC/input during sample, periodic30sQMP/startup
MT900strace remained enabled. Evidence `density-39-40-actual`,
`density-39-40-visual`, `owned-two-guest-strict-39-40*`.
N=2 observed pair only; no maxcapacity/cost/general compatibility claim.
CPU100%=onehost logical core; emulator RSS/PSS is not app allocation.

Initial/warm/process timing parsers and process/density samplers are tracked under
companion/. Exact OPEN needs fresh32lowerhex ID and CURRENT bootUUID; owned-control
creates the ID. Home must show actual app background before OPEN. No automatic
retry; acceptance does not prove app visibility. Loopback telemetry claimed PID is
checked against original owned path/uid501 and kernel identity, but peer PID is
not transport-authenticated. No new entitlements.

## Worker ownership

- boot_runner: actual builds/launch/staging/stopped evidence; no UI/input.
- native_probe: display trace source/audits; current worktree/tmp/inferno-display-query.
- disk_path: host command evidence/checkpoint changes; isolatedworktree.
- Root: integration/docs, all actual UI and control, image review.

Use followup_task to reactivate completed existing workers. Do not revert others.
Full historical facts, failed approaches and prior evidence remain in PROGRESS.md,
evidence/ and Git history; do not repeat crosscontainer file/extra-grant detours.
