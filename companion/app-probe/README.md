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
