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
| Separate app and resources | Runs75/77/79/81: distinct imported IPA launched, original process observed, reviewed bundled text and counter0→1, normal shutdown | Broader app coverage and repeatability |
| Xcode projects | Deferred by user; first release accepts already-built IPAs | A future build bridge needs macOS/Xcode and an actual recorded project build/run |
| Setup and operation | Source-pinned runner, private headless control and disk retention exist | Host preparation combines import, helpers, cache and recovery image with checked readbacks; prepare-import, stage-import and boot-import have each completed actual validation; repeatability and distribution setup remain |
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

The chronological record and current assignments remain in
[PROGRESS.md](../PROGRESS.md) and [NEXT_SESSION.md](../NEXT_SESSION.md).
