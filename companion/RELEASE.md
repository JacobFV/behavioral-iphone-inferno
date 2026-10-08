# First developer release

The target is a Linux runner for real iOS developer apps, with headless display,
input and captured execution evidence. It is currently a working prototype.
There is no release date supported by the remaining execution evidence.
The user selected already-built developer IPAs for the first release; a Mac/Xcode
builder will be added later, so Xcode-project building is deferred.

## Initial compatibility scope

- Pinned iOS 14 beta5 runtime and the tested ARM64 Linux host configuration.
- User-provided, unencrypted device IPAs meeting [the import subset](APP_IMPORT.md).
- Thin ARM64 executable, minimum iOS version at most 14.0, ordinary resource
  files and system dependencies. Actual dependency availability and behavior
  still require guest validation.
- External firmware, disks and build products. The repository supplies neither
  Apple firmware nor Apple SDK implementation binaries.

This scope does not establish compatibility with arbitrary App Store packages,
simulator binaries, nested frameworks/extensions, or current iOS APIs. An IPA is
a built application; an Xcode project also needs a separate build toolchain.

## Evidence and remaining gates

| Capability | Current evidence | Remaining work |
| --- | --- | --- |
| Real iOS boot, input and pixels | Original apps and owned UIKit app exercised; strict and warm/fresh-process journeys retained | Intermittent persistent display freeze remains unresolved |
| IPA import | Original fixture packaged as IPA; bytes preserved; archive, platform and encryption checks exercised | Broader compatible inputs and clear unsupported-input errors |
| IPA installation | Fixture and separate demo copied/read back with zero mismatches and clean unmount; prepared session2 passed normal recovery verification | Automated staging and the pinned boot-import wrapper passed installed demo journeys; broader app coverage remains |
| Separate apps and resources | Runs75/77/79/81 exercised a distinct imported app and bundled text; NavigationDemo also completed navigation, margin scrolling, switch/save and in-process state reopening | Verify revised button-start scrolling and unclipped text; broader app coverage and repeatability |
| Xcode projects | Deferred by user; first release accepts already-built IPAs | A future build bridge needs macOS/Xcode and an actual recorded project build/run |
| Setup and operation | Source-pinned runner, private headless control and disk retention; tracked helper build and plaintext recovery extraction reproduced prior artifacts byte-for-byte and passed actual host preparation and recovery staging | Fresh initial volumes, Data seeding and byte verification, flattening, capacity growth and SEP/keybag initialization passed; fresh cache inspection and host runtime artifacts also passed; cache patching, guest runtime installation, migration/setup and distribution setup remain |
| Reliability and resource use | Two simultaneous idle guests measured; individual active journeys retained | Repeatable release journeys and sustained active workload measurements |

The successful repeated counter runs do not establish that the earlier freeze
is fixed. Normal emulator exit does not establish app success. Import validation,
recovery readback, LaunchServices acceptance, original process presence, visible
resource loading and input response are distinct milestones.

The first byte-identical fixture IPA installed and launched, but its interactive
journey reproduced the persistent display freeze. The distinct resource-using IPA
completed visible counter0→1 in runs75,77,79 and81 without fixture telemetry. Run78
also completed the imported fixture’s strict counter journey. This does not
resolve that intermittent failure. Run85 repeated preparation and staging from a
persistent source tree, then launched the demo and loaded its resource text, but
the counter stayed0 after one acknowledged input. App callback receipt is
unproven; the attempt was retained as a failure and the wrapper refused normal
completion. Xcode support is outside the first-release milestone and needs an actual
project build and guest run before it can be advertised. Release
packaging follows those execution gates and the runtime reliability work.

The newly reproduced inputs also completed actual recovery staging, including
byte-for-byte app readbacks and a normal stop. The installed demo from that stage loaded its resource text but remained at
counter0 after acknowledged input and repeated observation. That attempt was
retained as a failure; staging alone does not establish app execution.

The setup guide now includes the complete local runtime descriptor and generic
headless operation steps. The helper and raw-image producers remove two one-off
host steps. Fresh initialization now also passed original role creation, Data seeding and a
separate read-only comparison (13,025 files, zero mismatches), host flattening,
original APFS capacity growth and SEP/keybag creation. Each retained its actual
raw evidence and stopped disk ancestry. These results are not an app-ready
runtime: fresh cache patching, owned-runtime installation and ordinary
Setup remain. The corrected read-only inspector subsequently reconstructed the
original launch configuration and matched the full original system-cache hash,
then stopped normally. Host preparation also produced the three owned launch
jobs and merged configuration with an exact decoded-content comparison. These
artifacts have not yet been installed on the fresh image. Runtime helper builds now have recorded source/tool pins and actual
command logs. Runs86–89 supplied further
healthy fixture journeys with diagnostic logging off, while run85 remains a
retained failed interaction. A direct generic demo journey in run90 also reached
counter1, while the reproduced wrapper attempt remains a failure. No
release-readiness claim follows from those passes.

NavigationDemo's first installed journey adds visible navigation/Back, scrolling
to item12, switch Off→On, Save and reopening the selected option. Original frames
and controls are retained in [the visual record](evidence/navigation-boot-1-visual/review.json),
with [normal shutdown and disk retention](evidence/navigation-boot-1-actual/review.json).
The initial sample did not scroll when a drag started on a button, and clipped the
last line of its bundled text. Sample-only corrections passed host build/import
and independent review; their guest behavior remains unverified. Saved state was
in-process only. This successful journey does not resolve the display freeze.

Fresh setup execution is currently blocked by storage: the next guarded flatten
requires34GiB free, while this host has approximately6GiB. Existing images and
backing chains remain preserved. Finishing that setup path, resolving the freeze,
and establishing the supported IPA set are the main gates before release packaging.

The chronological record and current assignments remain in
[PROGRESS.md](../PROGRESS.md) and [NEXT_SESSION.md](../NEXT_SESSION.md).
