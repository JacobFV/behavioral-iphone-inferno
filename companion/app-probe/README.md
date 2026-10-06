# Owned UIKit app probe

This small Objective-C app uses the guest's real UIKit and Foundation. It shows
a navy screen, cyan subtitle, white `Tap count: 0`, and a large orange
`INCREMENT` button. A touch-up-inside increments the visible count. It has no
network or account behavior. All declarations and text linker stubs here are
self-authored ABI descriptions; no Apple SDK or implementation is included.

Build with open-source clang and LLVM's Darwin linker, using a fresh output
directory outside the repository:

```sh
python3 companion/app-probe/build.py \
  --linker /absolute/path/to/ld64.lld \
  --output "$HOME/.local/share/inferno/app-probe/build-1"
```

The output contains `InfernoProbe.app`, the compiler object, exact command log,
and `build-evidence.json` with source/tool/bundle SHA256 hashes and Git revision.
The linker signs only this owned executable ad hoc. The builder inspects its
Mach-O signature and records the CodeDirectory flags/hash; there is no Apple
identity, provisioning profile, forged ticket or device key. Source hashes
identify any uncommitted source beyond the recorded Git revision. Keep output
outside Git. Tested host toolchain: Ubuntu clang18.1.3 and ld64.lld18.1.3 on ARM64
Linux. The executable links LC_MAIN with explicit guest libSystem, libobjc,
Foundation and UIKit dependencies; it is unencrypted ARM64 iOS14 code.

## Execution boundary and next integration

The bundle has compiled and linked; it has not run in the guest. The existing
owned native-probe helper has executed in recovery, and its `copyfile` path can
copy this bundle from a cloned recovery ramdisk onto a disposable mounted
volume. That is the evidence-backed staging mechanism available so far.
`companion/native-probe/prepare-root.c` owns the guest preparation flow. Do not
change an existing prepared disk to stage this app: use a new disposable copy.
The System volume is currently mounted read-only during that preparation;
staging this fixture would require an explicit writable phase and clean unmount.

Recovery has no established UIKit app launch route. Installed System boot is
still being brought up. LaunchServices registration, SpringBoard launch and
mobile installation have not executed; copying into `/Applications` alone is
not evidence of installation or launch. A future run must first establish the
full UI services, then use an observed registration/launch route or diagnose its
failure. This build does not grant signing-policy acceptance on a physical iPhone.

For an actual journey, capture the running app's framebuffer, then target the
large button using its observed bounds and capture `Tap count: 1`. The relevant upstream
handler is `hw/arm/apple-silicon/mt-spi.c` (`Apple Multitouch HID SPI`). It registers a legacy
absolute mouse handler, maps left-button state to touch and applies display
calibration. QMP absolute-axis events plus button press/release are the candidate
headless input path, still unproven for this app. Do not assume framebuffer
pixels equal UIKit points. The button occupies 80% of view width near 58% of
view height, away from screen edges.

Markers go to stderr and NSLog with prefix `INFERNO_UIKIT_PROBE_V1` and events
`main`, `window-visible-requested`, `view-loaded`, `appeared`, `active`, and
`tap count=1` (then subsequent counts). Stderr reaches serial only when the
launch route connects it there; capture the actual process/system log otherwise.
A requested window is not a captured visible screen. Acceptance needs the actual
before/after framebuffer and the matching interaction marker from the guest.

## Separate owned launcher

The same build produces `inferno-launcher` and the owned
`org.inferno.app-probe.plist` template. The app ID is now
`org.inferno.companion.probe`. Both executables are independently ad-hoc signed;
the evidence records both signatures and hashes. No privileged entitlement is
added on this initial attempt. The launcher uses self-authored declarations and
the original CoreServices implementation, not registration database fabrication.

Proposed staging on a NEW disposable disk only:

- Data: `/private/var/inferno/InfernoProbe.app` and
  `/private/var/inferno/inferno-launcher`, root:wheel; directories and executables
  mode0755, Info.plist0644. These are proposed readable/executable permissions,
  not proof that LaunchServices accepts this location.
- Owned job template: `/System/Library/LaunchDaemons/org.inferno.app-probe.plist`,
  root:wheel0644, requiring an explicit writable cloned System preparation phase.
  The job runs as mobile, routes stdout/stderr to `/dev/console`, and does not
  KeepAlive. Original launchd's embedded Bootstrap.Paths includes this directory,
  but not `/Library/LaunchDaemons`; no shipped launchctl was found in the inspected
  System inventory. A plist placed only on Data has no established bootstrap route.

The launcher calls `LSRegisterURL(bundleURL, false)` and logs its numeric OSStatus,
then queries `LSApplicationProxy` for validity, bundle URL, container and type.
Only after successful registration and valid proxy does it call
`LSApplicationWorkspace.openApplicationWithBundleID:`. It retries at most30 times,
with three seconds between attempts; default SIGALRM terminates the process after
120 seconds even if framework IPC blocks. An accepted open request exits0; retry
exhaustion exits1. A watchdog termination will not print an ordinary exit marker.
`request-accepted-not-visual-proof` explicitly means only service acknowledgement.
App markers and the actual screenshot/tap journey are still required.

The original same-build recovery CoreServices1114.5 binary was inspected:
`registerApplication:` at0x41f4c calls LSRegisterURL at0xd1838; `openApplicationWithBundleID:`
at0x3c700 returns a Boolean callback result. Its registration method explicitly
logs that it does not send the applicationsDidInstall notification, so an icon
appearing is not guaranteed. The helper calls LSRegisterURL directly to preserve
its numeric failure status. The System shared-cache variant and the whole route
remain unexecuted. The source symbol declarations are not a promise of acceptance.

If permission, container or signing policy rejects this honest owned bundle,
retain the actual error and inspect that rejection before changing the fixture.
No Apple signer identity is placed in registration dictionaries. The primary
[Procursus uiopen implementation](https://github.com/ProcursusTeam/uikittools-ng/blob/main/uiopen.m)
uses the same open-by-ID method; its [entitlement file](https://github.com/ProcursusTeam/uikittools-ng/blob/main/uiopen.plist)
provides launch privilege, but whether our guest requires that permission is
still an execution question. Do not copy its broad utility entitlement sets
without a demonstrated need.

## Disposable staging experiment

`build.py` also produces independently ad-hoc-signed `inferno-stage-app` from
`Stage.c`. `prepare-stage.py --help` describes the required verified decoded
recovery ramdisk, matching profile, built artifacts, HFS writer and fresh external
output. It clones the ramdisk, moves the original restored job out of LaunchDaemons,
adds owned assets and the owned stager job, then verifies every asset's readback
SHA256. It never uses HFS `rm`, which has an observed attribute-tree problem.

Run the resulting profile with the main boot runner's `--ramdisk-boot`, an
explicit stopped prepared root image and its SHA256, plus `--auxiliary-state`
pointing to the SAME stopped preparation report. The runner copies both root and
all six small namespaces; the keybag and its effaceable storage must stay paired.
Do not omit auxiliary state or reuse a live disk. Keep the original inputs.

The stager is intentionally specific to the verified prepared21 layout:
System `/dev/disk0s1s1`, Data `/dev/disk0s1s2`. It confirms the mounted System has
SystemVersion.plist and the Data volume is named Data. It requests original
`mount_apfs -o rw` and checks neither mount reports MNT_RDONLY before adding files.
It refuses an existing `/inferno` staging directory or any existing owned target;
no Apple file is overwritten. Original copyfile performs the four owned-file
copies, followed by ownership/mode setting and complete guest byte comparisons
against the ramdisk inputs. It then syncs and normally unmounts both volumes.

Accept staging only when raw serial contains all four matching byte comparisons,
`INFERNO_STAGE_UNMOUNT data=0`, `system=0`, and `INFERNO_STAGE_DONE result=0`.
Stop the recovery runner cleanly, hash the ENTIRE stopped disk set, and use that
report's root plus auxiliary state for the separate direct app-boot experiment.
Neither successful staging nor a launcher service acknowledgement proves an app
screen, launch or tap; the framebuffer and interaction evidence remain necessary.

Executed staging on 2026-10-06: sourcec325a4a3d2 built and ran against a copied
prepared21 root with its paired auxiliary namespaces. Raw serial at
`.local-build/reports/app-staging-1/serial.log` shows writable System mount,
Data identity, four successful full guest comparisons (71776,954,67952,844 bytes),
and both normal unmounts returning0. QMP quit after the completion marker returned
emulator exit0; the runner records an interrupted observation because SIGTERM
ended its requested240-second window early. The stopped root SHA256 is
`b9230ec175e388eb0da068adaa3a9fd2da07d63f1149332017aad73450893dca`;
all seven namespace hashes are in that report's `stopped-disk-hashes.json`.
The original prepared21 was unchanged. This proves owned-file staging only.

The first staged full-System boot reached launchd's early-boot completion, but
emitted no launcher marker and retained the Inferno startup frame through the
first120 seconds. Inspection then found432 jobs indexed by plist path in the
original `/System/Library/xpc/launchd.plist`. Adding a loose LaunchDaemons plist
alone is therefore not an established full-System job-loading route for this
image. The subsequent preparation must merge only the owned app/diagnostic job
entries into a cloned consolidated configuration while preserving original jobs;
that separate integration belongs to the native preparation worker. Do not claim
registration or app launch from successful file staging.
