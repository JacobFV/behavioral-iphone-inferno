# First developer release

The target is a Linux runner for real iOS developer apps, with headless display,
input and captured execution evidence. It is currently a working prototype.
There is no release date supported by the remaining execution evidence.

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
| IPA installation | Actual recovery copied and read back 75,930 bytes with zero mismatches and clean unmount | Imported app launched, but counter presentation froze in74; interactive gate failed |
| Separate app and resources | Different bundle ID, resource-loading demo and manifest-bound launcher built; imports audited against original cache | Fresh target installation, original process evidence, reviewed resource text and counter response |
| Xcode projects | Build/runtime boundary defined | Available macOS/Xcode builder, recorded project build, resulting IPA passed through the same execution path |
| Setup and operation | Source-pinned runner, private headless control and disk retention exist | Reproducible documented setup, fewer manual integration steps and actionable failures |
| Reliability and resource use | Two simultaneous idle guests measured; individual active journeys retained | Repeatable release journeys and sustained active workload measurements |

The successful repeated counter runs do not establish that the earlier freeze
is fixed. Normal emulator exit does not establish app success. Import validation,
recovery readback, LaunchServices acceptance, original process presence, visible
resource loading and input response are distinct milestones.

The first byte-identical fixture IPA installed and launched, but its interactive
journey reproduced the persistent display freeze. Next is the distinct
resource-using IPA with no fixture telemetry. Xcode support needs
an actual project build and guest run before it can be advertised. Release
packaging follows those execution gates and the runtime reliability work.

The chronological record and current assignments remain in
[PROGRESS.md](../PROGRESS.md) and [NEXT_SESSION.md](../NEXT_SESSION.md).
