# Owned UIKit app probe

This small Objective-C app uses the guest's real UIKit and Foundation. It shows
a navy screen, cyan subtitle, white `Tap count: 0`, and a large orange
`INCREMENT` button. A touch-up-inside increments the visible count. Its diagnostic
event transport connects only to guest loopback127.0.0.1:37373; it has no external
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

Installed iOS14 beta5 now reaches SpringBoard Home and launches original Clock.
The owned fixture is registered with the original LaunchServices dictionary API.
The exact `/Applications/InfernoProbe.app` path is classified as `System`, matching
original installd's normal classification. A normal restart after that correction
changed the original FrontBoard result from Security3 to accepted with no error.
No signer, profile or trusted-state fields were invented.

Boot25 executed the owned process through UIApplicationMain, then crashed when
UIKit retained its delegate. Our narrow NSObject declaration had omitted the
original eight-byte isa header: compiled `_window` stores overwrote self+0.
The corrected declaration preserves that header, and actual build14 instructions
store/load `_window` at self+8. Boots26,27 and28 each captured the fixed app at counter0, then counter1
after one explicit counter tap. See `../evidence/owned-app-isa-fix/` and
`../evidence/migration-first-unlock/owned-app-first-crash-25-analysis.json`.

Stage only on a new disposable copy or validated writable overlay of a normally
stopped, hash-verified paired disk tuple. Retain every immutable backing layer. The original recovery copyfile path supports an executable-only
replacement and byte/metadata readback, followed by normal unmount. Preserve
unchanged components when isolating a change; record every replaced binary.

For an actual journey, review the app framebuffer before targeting its large
button and capture the visible change from `Tap count: 0` to `Tap count: 1`.
The owned virtual touchscreen has delivered actual setup and stock-app input;
its private serial mailbox requires an explicit operator request. The default
`--probe-journey` only observes and never sends a gesture. The legacy hardware
MT-SPI path remains unready and must not be substituted for proven input.
Do not assume framebuffer pixels equal UIKit points. The button occupies80% of
view width near58% of view height, away from screen edges.

Markers go to stderr and NSLog with prefix `INFERNO_UIKIT_PROBE_V1` and events
`main`, `window-visible-requested`, `view-loaded`, `appeared`, `active`, and
`tap count=1` (then subsequent counts). Stderr reaches serial only when the
launch route connects it there; capture the actual process/system log otherwise.
The current FrontBoard route does not send app stderr to the console. The app's
original Foundation cache path now writes successfully, but the separate helper
cannot read the container file: actual31 found its exact descriptor and metadata,
then open returned errno1. The new bounded loopback transport sends the same
actual records directly from the app. Its receiver checks the boot UUID, claimed
PID's exact executable and uid, grammar and sequence before preserving the raw
line and emitting a marker. This checks the claimed PID; TCP peer PID is not
authenticated. It is fixture telemetry, not a security authentication protocol.
Boot32 proved guest bind/connect/relay with actual lifecycle and tapcount1
records and strict before-capture. Its unexpected Signal15 preceded operator
after-capture, so strict completion remains pending in repeat33. Missing markers
must still fail the strict runner.
A requested window is not a captured visible screen. Acceptance needs the actual
before/after framebuffer and the matching interaction marker from the guest.

## Separate owned launcher

The same build produces `inferno-launcher` and the owned
`org.inferno.app-probe.plist` template. The app ID is now
`org.inferno.companion.probe`. Both executables are independently ad-hoc signed;
the evidence records both signatures and hashes. No privileged entitlement is
added on this initial attempt. The launcher uses self-authored declarations and
the original CoreServices implementation, not registration database fabrication.

Historical initial Data-path staging proposal (not the current installed path):

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

The current launcher calls original `registerApplicationDictionary:` with the
owned Info.plist, actual Path and exact System classification described above,
then queries `LSApplicationProxy` for validity, bundle URL, container and type.
Only after successful registration and valid proxy does it call
`openApplicationWithBundleIdentifier:configuration:completionHandler:` with a
nil configuration and the original BOOL/NSError callback. It retries at most30 times,
with three seconds between attempts; default SIGALRM terminates the process after
120 seconds even if framework IPC blocks. An accepted open request exits0; retry
exhaustion exits1. A watchdog termination will not print an ordinary exit marker.
`request-accepted-not-visual-proof` explicitly means only service acknowledgement.
Strict acceptance also requires app markers and reviewed before/after captures.
The visual journey and event relay are proven; both strict operator captures
in one uninterrupted run remain the current acceptance target.

The original same-build recovery CoreServices1114.5 binary was inspected:
`registerApplication:` at0x41f4c calls LSRegisterURL at0xd1838; `openApplicationWithBundleID:`
at0x3c700 returns a Boolean callback result. Its registration method explicitly
logs that it does not send the applicationsDidInstall notification, so an icon
appearing is not guaranteed. LSRegisterURL is a local function, not an exported
interface in this guest. An earlier direct import caused an actual missing-lazy-
symbol SIGABRT in app-boot-5 at launcher offset0x417c (return from the call at0x4178).
The corrected helper invokes the original Objective-C method and reports BOOL,
not a fabricated OSStatus. The subsequent dictionary route registered successfully; the corrected System
classification and a normal restart produced actual accepted launches25–28.

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

`app-boot-1` completed its240-second observation with seven identical30-second
captures (SHA256 `fd27fc149822f9f986de68f276a382ea7e2bf9ed4a5ba54f60c757c075ef9d7c`),
visually reviewed as Inferno branding. No owned launcher or app marker appeared.
The strict journey failed `waiting-for-app`; QMP quit returned emulator exit0.
Raw logs, frame captures, binary/source identity and QMP transcript are retained
under `.local-build/reports/app-boot-1/`. This is a job-loading boundary before
any observed registration call, not evidence of a failing registration API.

`prepare-stage.py --inspect-only` builds a recovery job that mounts System and Data
read-only, logs owned-path lstat mode/owner/size, compares the four owned assets,
and normally unmounts without staging changes. Actual `app-path-inspection-1`
against a copy of stopped preparation23 found all owned files intact and byte-equal;
launcher was67952 bytes, regular0755 root:wheel, with readable0755 parent directories.
The installed launcher's SHA256 is
`0a95bb65be29149522d321c527de7efb17b4d3a9a8b5e4d68c4081110c479476`
from `stage-committed/build-evidence.json`. The earlier launcher-only build has a
different hash and must not identify these staged bytes.

`app-boot-2` then ran360 seconds: the diagnostic job and original SpringBoard and
backboardd processes executed, while launchd reported the owned launcher as a
missing executable. That message can also denote executable-access or architecture
failure; it does not prove deletion. The boot log explicitly mounts Data at
`/private/var`, so changing to a nested private/var Data layout is unwarranted.
Host inspection found both launcher and actually executed readiness helper are
ARM64/ALL, iOSminimum14, LC_MAIN offset16384, `/usr/lib/dyld`, PIE, cryptid0 and
LLVM ad-hoc signed. Launcher adds Foundation/CoreServices/libobjc dependencies.
Framebuffers advanced from Apple logo to a moving progress bar around43%; a
precautionary migration stackshot is not proof of a hard deadlock. Post-boot
file/access inspection and preserving the paired migration state are the next
checks. No app execution or touch is established.


`launcher-load-1` exercised the exact staged launcher in an independent recovery
ramdisk with no arguments and no prepared disks attached. It emitted usage through
stderr and NSLog, then returned exit64 (raw wait status16384), as expected. The
launcher SHA256 remained `0a95bb65be29149522d321c527de7efb17b4d3a9a8b5e4d68c4081110c479476`.
This establishes executable/dependency loading in recovery, not registration or
launch in the full System environment. `prepare-stage.py --launcher-noargs`
reproduces this bounded read-only invocation.

`inferno-exec-launcher` and `org.inferno.app-probe-exec.plist` are a prepared,
not-yet-executed diagnostic alternative. Install the owned wrapper on System at
`/usr/bin/inferno-exec-launcher`; replace only the owned `org.inferno.app-probe`
consolidated job with this template (same Label), avoiding a duplicate launcher.
The root wrapper logs its identity, forks, clears supplementary groups, drops to
mobile gid501/uid501, logs that identity and execs the unchanged Data launcher and
app paths. It records exec errno or child wait status. The parent polls up to150
seconds, kills only its own child on timeout and reaps it. No added entitlements,
Apple job edits or alternate registration identity are involved. Staging requires
a stopped copied disk set; the active migration run remains untouched.


`app-exec-diagnostic-1` now executes the System wrapper: root uid/gid0, child
uid/gid501, then Data launcher `execve` fails with EPERM(1); child exits127
(raw32512), without timeout. The240-second run ends through QMP quit, emulator0,
and strict app journey remains waiting. No explicit AMFI/sandbox denial was
printed adjacent to the failure, so EPERM does not establish its cause.

`org.inferno.app-probe-matrix.plist` selects `--matrix`: Data/root, Data/mobile,
and System/mobile each run the exact launcher bytes with no arguments, expect
exit64, and have a60-second child bound. The latter case requires an owned exact
copy at `/usr/bin/inferno-launcher`. Each child logs executable/read access and an
actual read of up to16KiB before exec (the Mach-O header region). This separates credentials and volume effects
without making registration calls as root. This matrix is prepared, not yet run.


`app-exec-matrix-1` executed all three cases. Data/root and Data/mobile both
returned X_OK=-1/EPERM and execve=-1/EPERM, while R_OK, open and16384-byte read
succeeded. The identical System launcher under mobile passed access/read,
printed actual usage through stderr and NSLog and exited64 as expected. No child
timed out. The run was deliberately ended after those results with runner SIGTERM,
QMP quit acknowledged and emulator0; this is not a360-second observation. The
independent long migration run remained active. Evidence establishes a working
System/mobile launcher location, not app registration or Data app execution.


`audit-imports.py` checks fixture and launcher bind/lazy-bind entries against the
original monolithic shared cache's Mach-O export tries and explicit reexport
chains. It deliberately does not accept local/debug symbols as exported APIs.
The corrected build8 audit resolves53 imports, while the old launcher's
LSRegisterURL import is absent. The audit requires an explicit original cache,
LLVM objdump and output path; all binary inputs remain outside Git. Runtime method
behavior and registration policy still require actual guest execution.


The corrected launcher in `app-boot-6` reached original
`registerApplication:` and observed NO repeatedly, with an invalid application
proxy and nil bundle URL for the Data app. This is an actual registration result,
not an inferred execution failure. No numeric OSStatus is available from this BOOL
method. The caller's120-second alarm eventually ended that attempt with signal14.

A prepared controlled variant uses wrapper `--system-app` and
`org.inferno.app-probe-system-app.plist` to target `/Applications/InfernoProbe.app`.
The original System inventory contains root `Applications/MobileSMS.app` and
`Applications/Setup.app`, establishing this directory layout. Stage only the exact
owned bundle bytes while retaining the Data copy: executable SHA256
`c11f4d430ee8543da2bdade55e5f5beb8685692345dc6fe2ccbad114ad6f55ec`, Info.plist
`ad9946fd7093f8f438f70200f5e096667e47989da70be2187a7324c6ed20a153`.
No alternate signer identity or registration dictionary was introduced in this
path comparison. Actual `app-boot-7` System-path attempts also returned NO and
invalid proxies; completed batches exited1. Raw evidence and stopped disk hashes
are retained under `companion/evidence/app-system-registration*`.

`DictionaryLauncher.m` now builds a separate `inferno-launcher-dictionary`
candidate. Original control-flow inspection in
`registration-path-inspection.json` shows that the URL route passes a NULL
registration dictionary and can skip new-bundle registration, whereas original
`registerApplicationDictionary:` passes that dictionary into the registration
path. The candidate reads the exact owned Info.plist, verifies its bundle ID,
adds only the actual `Path`, and logs the original BOOL result as
`register-dictionary-boolean`. It adds no entitlements, signing metadata,
container records, or alternate identities. The URL executable and app retain
their prior hashes; both variants remain independently buildable.

Build10's original-cache export audit resolves all71 imports across the two
launchers and app. This verifies imports, not registration or execution. The
dictionary candidate is prepared for a separate staged comparison; the first
SEP protocol comparison continues with the unchanged URL launcher.

Actual `app-boot-10` dictionary registration returns YES with a valid proxy at
the owned System bundle path. The original open request still returns NO; this
is registration success, not app execution. `DiagnosticLauncher.m` builds a
third separate candidate, `inferno-launcher-open-error`, using original
`openApplicationWithBundleIdentifier:configuration:completionHandler:` with nil
configuration. Its inspected BOOL/NSError callback logs bounded domain, code and
localized description. `open-path-inspection.json` records the synchronous proxy
and block ABI evidence. No callback wait or new launch options are invented;
the existing process watchdog remains. Build11's original-cache audit resolves
all90 imports across the three launchers and app. Earlier launcher and app
artifacts retain their exact hashes. Actual `app-boot-11` callback returns
accepted=0, NSPOSIXErrorDomain code60 (operation timed out), which is not proof of
an app execution denial. Completing the original options-helper trace shows
that even nil configuration automatically adds `LSBlockUntilComplete=true`.
This is the original method's waiting behavior, unlike the empty-options BOOL
wrapper; the candidate does not supply explicit launch options.

## Owned System bundle registration

The dictionary launcher supplies `ApplicationType=System` only for the exact
owned identifier `org.inferno.companion.probe` at `/Applications/InfernoProbe.app`.
This reproduces the installed iOS installer's classification: an identified `.app`
whose parent is its configured `/Applications` directory receives type1, rendered
as `System` in the LaunchServices dictionary. See
[original classification evidence](../evidence/owned-system-app-classification-inspection.json).
Omitting the field had produced the original `User` fallback and the observed
FrontBoard/MIS signature-validation denial. The fixture remains independently
ad-hoc signed; no Apple signer, provisioning profile or trust-result metadata is
asserted. Actual launch must still be verified from guest markers and captures.
