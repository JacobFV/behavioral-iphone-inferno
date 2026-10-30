# Journal: running real iOS on Linux, step by step

A dated lab notebook of what we tried, what happened, and what we'd tell someone starting
from scratch. Kept so that we (and anyone else doing this) don't repeat the same hours.
It never contains Apple binaries, keys or decrypted firmware; you bring your own IPSW.

## From zero to a working iPhone on Linux (current recipe)

Host: Ubuntu 24.04 arm64 (tested on two NVIDIA GB10 boxes, CPU emulation only). About
130 GiB free disk for one full chain plus a few boots; keep the repo at the same absolute
path on every host (stage records hash absolute paths).

1. **Emulator.** `companion/build-linux.sh --build-root "$PWD/.local-build" --jobs 8`, then
   `./companion/run check` (firmware-free QMP smoke). Or copy an existing `.local-build`
   whose `build-manifest.json` matches.
2. **Firmware.** Put `iPhone11,8,iPhone12,1_14.0_18A5351d_Restore.ipsw` (iOS 14.0 beta 5) in
   `$INFERNO_HOME/ipsw/` (default `~/.local/share/inferno`). Check its sha256 against
   `companion/os-image/README.md`.
3. **System image.** `./companion/run prepare --ipsw …`, then `os-image/decode-udif.py` and
   `wrap-gpt4k.py`. The four hashes (DMG `cae20aff…`, raw `96bebe30…`, APFS `54f0ea7d…`,
   GPT wrapper `93f97dae…`) must match; they did on a second machine
   (`evidence/second-host-reproduction-1/`).
4. **Host tools** outside Git, under `$INFERNO_HOME`:
   - `disk-overlay-tools/`: the pinned Ubuntu `qemu-utils` `qemu-img` (`disk_overlay.py`
     bootstrap; packages and hashes in its `tool-provenance.json`);
   - `native-probe/tools/`: `ld64.lld-18` (`apt download lld-18`, extracted, not installed),
     `hfsplus`;
   - `native-probe/ldid`: the pinned ldid.
   Building the helpers needs clang; if the emulation host has none, build them on another
   arm64 Linux box and copy them over. Signed outputs come out byte-identical.
5. **Owned helpers** (each writes a `build.json` the later stages pin):
   `native-probe/build-prepare-helper.py`, `build-grow-helper.py`, `build-runtime-helpers.py`,
   `runtime-inspector/build.py`, `fs-patches/build-cache-helper.py`.
6. **Recovery extraction and the fresh chain.** `companion/tour/chain-all.sh SUFFIX` runs every
   stage with hash pinning: initial volumes → Data seed → verify → flatten → grow → SEP keybag
   → flatten keybag → runtime inspection → renderer cache patch → fresh-runtime artifacts →
   fresh-runtime stage. Copy `tour/env.example.sh` to `~/inferno-chain/env.sh` first.
   Roughly 2–3 hours on one GB10.
7. **Setup Assistant.** `boot-fresh.py` from the fresh-runtime stage, then answer Setup
   Assistant with ordinary gestures through `owned-control` (~25–37 gestures). When it shows
   "Welcome to iPhone", setup completion is already persisted: stop it with
   `qmp_control.py finish-observation`, run `preserve-stopped.py`, and `chmod a-w` its disks.
   That boot's `boot/report.json` is your **setup-complete base**.
8. **Use it.** Every boot from the base starts at the lock screen:
   `companion/tour/tour-cycle.sh PLAN N` unlocks, dismisses system alerts, and tours apps from
   a JSON plan, restarting on the display freeze.

## 2026-10-29: a second host, a fresh device to Home, and 21 apps

**Question: does the chain reproduce off the original machine?** The original
`~/.local/share/inferno` (firmware, tools, staged disks) had been deleted, and the only image
that had ever reached Home was built on a base that no longer existed.

- Copied repo + `.local-build` + IPSW to `promaxgb10-4dfb` at the same paths.
- `run check` passed; prepare/decode/wrap reproduced all four image hashes byte-for-byte.
- Rebuilt the four missing host tools from the pinned recipes (above) and every helper;
  outputs were byte-identical to the reviewed records except where noted below. `ldid`'s own
  binary hash differs per build; what it signs does not.
- The original dyld shared cache was re-extracted and re-patched with the pinned
  InfernoFSPatcher; both full-file hashes matched the recorded values.
- **Two host pins broke the chain** (fixed in `8a75e20`):
  - helper build records hash host tool paths and the ldid binary, so a byte-identical
    rebuild on another host was refused → now accept a build whose *outputs* equal a
    reviewed record's outputs;
  - four stages always validated under `runtime_rebuild.historical()` (which maps the rebuilt
    emulator back to the lost one), so a chain made entirely with the rebuilt emulator failed
    its own pins → enter `historical()` only when the reports don't record the rebuild.

**Question: why did fresh Setup Assistant always stop at "Welcome to iPhone"?**
Earlier (fresh-boot-6, 11 Oct) this looked like an iOS problem. It wasn't.

- A second-host rerun stopped at *App Analytics* with `INFERNO_HID_EXIT requests=32`.
- The guest HID helper accepted **32 gestures per boot** (and lived 7200 s); the host
  transport enforced the same 32 and a 42-entry request-ID set. Setup needs ~25 gestures
  before Home plus retries, so every fresh attempt ran out of budget right at the end.
- Raised to 2048 requests / 21600 s / 2100 IDs, named once per side
  (`INFERNO_HID_MAX_REQUESTS` / `HID_MAX_REQUESTS`) — `2f03b87`, approved build `0e374d1`.
- Result: setup finished in **37 acknowledged gestures**. "Welcome to iPhone" still does not
  visibly advance, but completion is persisted (as in historical boots 22/23); every later
  boot from the stopped state comes up at the lock screen.
- Lesson: when a fresh device "stalls", check the control channel's own budgets and exit
  lines before suspecting the guest.

**Tour harness** (`companion/tour/`, `3671406`, `83b97aa`):
- boot from the base → wait for lock screen → unlock (1500 ms swipe) → `bringup.py` dismisses
  the beta-update and "Finish Setting Up" alerts (detected by the dimmed background) →
  `app-tour.py` opens each app in a JSON plan, does taps/swipes, returns Home → records the
  display at 1 Hz via a no-input VNC observer.
- The documented compositor freeze is detected when the status-bar clock is unchanged across
  two whole apps (`--freeze-dir`, exit 3); the cycle stops that boot normally and boots again,
  resuming one app earlier.
- Two system alerts arrive late after unlock and ate time in boots 2–3 until `bringup.py`
  learned them.

**Results** (`evidence/app-tour-1/`): two passes over the 23 apps on page 1 and the dock.
Opened and used: Settings, Clock, Notes, Health. Real first-run or content screens: Calendar,
Photos, Books, Wallet, Home, TV, News, Mail, Safari, Messages, Music, Phone, FaceTime, Weather,
App Store. Blank: Reminders, Podcasts. Quit to Home on launch: Maps, Stocks. Network-dependent
apps show offline states (no network in the guest yet).

**Freeze statistics:** the display froze in **5 of 10 tour boots** (boots 3, 5, 6, 8, 9), every
3–16 apps; each restart costs **~12 minutes** to the lock screen. Still the main reliability
problem (`FREEZE_HYPOTHESES.md`).

Video: 248 s, frames scaled never edited, published on jvboid.dev (iPhone on Linux).

## 2026-10-29 (afternoon): pruning, and how to give the guest a network

**Prune.** The base's real backing chain (read with the pinned `qemu-img info --backing-chain -U`)
is `fresh-boot-r6/root.qcow2 → fresh-r6 → cache-r6 → flatk-r6/root.raw`. Kept every `*-r6` stage,
`ipa-demo-r2` (an input of `ain-r6`), `images/`, the IPSW, `cachework/`, tools and helpers. Deleted
the ten tour boots, `fresh-boot-r1` and every superseded r2–r5 stage (27 directories, listed with
sizes in the host's `~/inferno-chain/prune-2026-10-29.tsv`). 137.3 GB of apparent size; the
filesystem gained ~51 GB (sparse files). Inferno state went 107 G → 56 G. Two
`KEEP-OVERLAY-BACKING.json` markers named deleted directories, but only as *consumers* of a kept
disk, never as backing files, so they don't block anything.

**What the emulated iPhone 11 offers for networking.** No Wi-Fi or Ethernet model exists in the
t8030 machine. Its only external link is USB: `apple_otg` wraps QEMU's DWC2 (extended for device
mode) and the far end is `usb-tcp-remote`, which a Linux "USB companion" VM attaches to (USB.md;
run9 already saw `ideviceinfo` report 14.0/18A5351d from an installed boot).

Dead ends considered:
- Emulating Wi-Fi (BCM4378 over PCIe with firmware): far too deep.
- iPhone as USB *host* with an emulated USB-Ethernet dongle: needs Lightning/accessory role
  detection to flip the OTG into host mode.
- A `utun` tunnel from a root helper over a spare UART: workable in principle (9 UARTs exist,
  only `/dev/console` is used), but needs a new guest helper, SCDynamicStore DNS/primary-service
  plumbing and a host NAT, and apps may still see "no Wi-Fi/cellular".

**Chosen: reverse tethering over USB CDC-NCM.** iOS ships device-side NCM ("computer shares its
internet with the iPhone"). The decompressed iOS 14.0 kernelcache contains `AppleUSBDeviceNCM`,
`AppleUSBDeviceNCMData`, `kVendorRequestSelectExtendedFunction` and `ncm-interrupt-ep-disabled`
(decompress: find `bvx2` in the im4p and call `lzfse_decode_buffer` from the repo's liblzfse).
On Linux the switch is the vendor request usbmuxd sends for `USBMUXD_DEFAULT_DEVICE_MODE=3`:
`bmRequestType 0xC0, bRequest 0x52 (SET_MODE), wValue 0, wIndex 3, wLength 1` (`0x45` reads the
mode). After re-enumeration select configuration 5; `cdc_ncm` binds; give the host side an
address, run DHCP/DNS (dnsmasq), and NAT out through the companion's own user networking.
(Reference: Synacktiv, "iOS: a journey in the USB networking stack".)

## 2026-10-29 (evening): installing more apps, the GPU answer, and how far networking got

**Installing apps onto a setup-complete device (works, ~2 min per app).** Re-running the fresh
chain to add an app would mean redoing Setup Assistant. Instead `prepare-import` / `stage-import`
now target the setup-complete base directly:
- `tour/make-runtime-record.py` writes the `inferno.local-ipa-runtime.v1` record from the fresh
  chain's own evidence (`fresh-r6/recovery-run` profile/report/serial with its
  `INFERNO_CACHE_READBACK`, `art-r6/launchd.plist`, `fresh-r6/recovery/preparation.json`).
- The overlay depth cap was 4, and a fresh base is already 4 layers deep; raised to 10
  (`MAX_OVERLAY_DEPTH`, shared by `disk_overlay`, `prepare-import`, `import_stage`).
- `stage-import`'s "no other emulator" preflight now ignores the USB companion VM.
- The emulation host had no clang: Ubuntu's clang-18 debs (`apt-get download`, `dpkg-deb -x`)
  plus a 3-line wrapper setting `LD_LIBRARY_PATH` work without root
  (`native-probe/clang18/clang`).
- `tour/build-objc-app.py` builds small Objective-C apps (several sources, per-app `.tbd`
  overrides, resources) into import-validated IPAs.
- Caveat: all imports share one launcher job slot (`org.inferno.app-probe.plist`), and each import
  adds two overlay layers (recovery + boot), so ~3 apps can be chained per image before a flatten
  step is needed. `tour/try-app.sh NAME IPA` does import → boot → unlock → record → stop → contact
  sheet for one app.

**The graphics answer (`gpu-probe/`).** In the emulated iPhone 11 on iOS 14.0b5:
Metal.framework loads but `MTLCreateSystemDefaultDevice()` returns **nil**; OpenGLES.framework
and `EAGLContext` load but **neither an ES3 nor an ES2 context can be created**; SpriteKit and
QuartzCore (`CAMetalLayer`) load; ordinary CPU-composited UIKit views draw correctly. So anything
that needs a GPU device (Metal/GLES games, SDL with a GPU renderer, SpriteKit scenes) won't
render; UIKit/Core Animation software paths do.

**Networking: reverse tethering gets to "interface up, unconfigured".**
- USB companion VM (Ubuntu Noble cloud image, TCG because this user has no `/dev/kvm` access on
  the second host) attaches to the iPhone's USB transport; the phone enumerates as `05ac:12a8`.
- `net/ncm-mode.py set 3` (vendor request `0x52`, index 3) works: the phone re-enumerates with a
  5th configuration "PTP + Apple Mobile Device + NCM" (interfaces: PTP, usbmux, CDC-NCM control
  class 2/13 with interrupt EP 0x86, NCM data 10/0 with alt 1 bulk EPs 0x87/0x05).
  iOS logs `IOUSBDeviceController::setupDeviceSetConfiguration: configuration 4 -> 5`.
- The cloud kernel lacks `cdc_ncm`: install `linux-modules-extra-$(uname -r)`. Then `cdc_ncm`
  binds as `enxdeadbeef22ed` (iOS's NCM MAC is `de:ad:be:ef:22:ed`).
- iOS answers `GET_NTB_PARAMETERS` (NTB16 only, 12144-byte NTBs, divisor 4, alignment 4, 8
  datagrams) and accepts the data alt-setting from userspace (`net/ncm-probe.py`).
- **Inside iOS** (`net-probe/`, an owned app showing `getifaddrs` + TCP tests on screen): `en0`
  is UP,RUNNING with only a link address — no IPv4, not even an IPv6 link-local — and `en1` is
  down; `utun0/1` exist. TCP to 192.168.77.1 and 1.1.1.1 time out.
- **On Linux**: NO-CARRIER, zero frames either way. iOS never sends the NCM NetworkConnection
  notification.
- Reading: the NCM interface exists and is up, but configd has no network service for it, so
  IPConfiguration never runs DHCP (on a real iPhone the reverse-tethering service is set up by the
  system when a Mac shares its connection). Next step: an owned root helper in the guest that
  creates that service (SCPreferences) or configures `en0` directly (address/route via ioctl +
  SCDynamicStore DNS), plus forcing carrier on the Linux side (or bridging NCM from userspace with
  `ncm-probe.py`'s approach, which bypasses `usbnet`'s carrier gate).
- Dead end noted: GStreamer can't decode the Remotion mp4; use the compositor ffmpeg.

**Swift / SwiftUI / storyboard IPAs from the build farm.** Importer changes (`app-import.py`):
embedded `MH_DYLIB` Mach-Os under `Frameworks/` (thin arm64, minos ≤ 14, unencrypted), `@rpath`
dependencies resolved against the loader's rpaths *and the main executable's* (Apple's
back-deployed `libswift_Concurrency.dylib` has none of its own and relies on the app's
`/usr/lib/swift` rpath), `/usr/lib/swift` names accepted as guest-cache libraries, Mach-O files
get mode 0755. `tour/prepare-swift-ipa.py` strips `PlugIns/`, drops names outside the importer's
character set (NetNewsWire's `AppIcon@2x.png` etc.; the guest copy helper allows only
`[A-Za-z0-9_. -]`), and re-signs every Mach-O with `ldid -S` innermost first. Result: HelloSwiftUI,
HelloStoryboard, HelloAsync and NetNewsWire 6.0 all pass import validation. Running them is
in progress (`try-app.sh`).

**First Swift run (HelloSwiftUI, Xcode 16.4, ad-hoc re-signed with ldid).** After import onto the
setup-complete base and one boot, LaunchServices registered it (icon "Hello SwiftUI" appears on
Home page 2) and the launcher's open was accepted; the process list shows
`/Applications/HelloSwiftUI.app/HelloSwiftUI` running as uid 501 with no crash report. So iOS 14
loads an Xcode 16.4 / iOS 18.5-SDK Swift binary and its ldid signature. Its on-screen rendering is
not captured yet: `session.sh`'s alert bring-up pressed Home and backgrounded it; tap the icon in
the next tour. Page 2 of Home in this build: Files, Find My, Shortcuts, iTunes Store, Translate,
Contacts, Watch, Tips, a Utilities folder, Feedback (plus imported apps).

## 2026-10-29 (late): a root network helper, a userspace NCM bridge, and building OSS apps on Macs

**Why `en0` never got an address.** Nothing in the guest owns it: configd has no network service for the
NCM interface, so IPConfiguration never runs. Instead of creating a configd *Setup* service, give the
interface what a service would have produced:
- `app-probe/NetHelper.h`, compiled into the per-import root launch wrapper (`ExecLauncher.c`, which
  launchd already runs as root at boot via `org.inferno.app-probe`). Before dropping to mobile it forks a
  root child that polls for `en0` every 3 s and, when `en0` lacks 192.168.77.2, does
  `SIOCAIFADDR` (192.168.77.2/24), adds a default route to 192.168.77.1 via a `PF_ROUTE` `RTM_ADD`
  message, and publishes configd *State* keys with `SCDynamicStoreSetValue` (reached through
  `dlopen`/`dlsym`, so no SDK headers): `State:/Network/Interface/en0/Link {Active}`,
  `State:/Network/Service/org.inferno.ncm/IPv4 {Addresses, SubnetMasks, Router, InterfaceName}` and
  `.../DNS {ServerAddresses}`. IPMonitor turns those into the primary service, routes and the resolver.
  Serial log line: `INFERNO_NET_CONFIGURED if=en0 addr=… route=… publish=…`.
- The libSystem link stub gained `_dlopen _dlsym _ioctl _if_nametoindex _usleep`.

**Why Linux saw NO-CARRIER.** `cdc_ncm` waits for the NCM NetworkConnection notification, which iOS never
sends, and usbnet moves no frames without carrier. `net/ncm-bridge.py` (run as root in the USB companion)
skips the kernel driver entirely: pyusb claims the NCM control and data interfaces, selects data alt 1, and
copies frames between NTB16 transfers and a TAP device (`ncm0`, 192.168.77.1/24), with dnsmasq for DNS and
NAT out through the companion's uplink.

**Recording imported apps.** `tour/bringup.py` pressed Home after clearing alerts, so `try-app.sh` recorded
the home screen instead of the app (HelloSwiftUI's first run). `BRINGUP_NO_HOME=1` (set by `try-app.sh`)
leaves the launched app in the foreground.

**OSS apps: build on Macs, not Linux.** Building Puzzles/Tipulator/jot/vfr Reader on Linux needs ARC,
blocks, CoreGraphics/CoreText and much more UIKit in our hand-written headers (days). Since Xcode-built
IPAs now pass the importer and HelloSwiftUI runs, the faster route is the GitHub Actions macOS farm
(`JacobFV/ios-build-farm`, `scripts/oss/*.sh`): Puzzles, Tipulator, jot (CocoaPods), vfr Reader,
ACEDrawingView. The Linux-native path stays the long-term, Mac-free option.

**OSS builds on the macOS farm (all Xcode 16.4, minos 14.0, unsigned).** First tries and fixes, in
`JacobFV/ios-build-farm` `scripts/oss/`:
- ACEDrawingView demo (Apache-2.0, vendored Pods): built first try, 50 s.
- vfr Reader (PDF): built first try, 80 s (no shared scheme; `xcodebuild -list` auto-creates one).
- jot / JotDemo (MIT): `pod install` after raising the Podfile platform to 14.0; 45 s.
- Puzzles (Simon Tatham's, iOS port): failed on `svnversion.c`, which a script phase generates from
  `git merge-base HEAD simon/master` (a remote a fresh clone lacks) and which the compile can reach
  first. Writing it up front fixed it; 139 s.
- Tipulator (MIT): two failures. The xcconfig `#include`s HockeySDK from a submodule that is no longer
  public, and the target links its static library, resource bundle and PLCrashReporter. A small patch
  (`patches/tipulator-drop-hockeysdk.py`) removes the include, the three project references, the
  dependency targets and the manager calls. It also has no `Release` configuration, so
  `build-ipa.sh` now takes `CONFIGURATION` (Tipulator uses `Distribution`).

**Retina assets were being dropped.** `prepare-swift-ipa.py` dropped every `@2x`/`@3x`/`~ipad` file
because the importer (and the guest copy helper `imported-app.c`) allowed only `[A-Za-z0-9_. -]`.
For Puzzles and Tipulator that is most of the artwork. Allowed `@ ~ +` in all three validators and
rebuilt the preparation helper (`reproducible-helper-build-r3`, built on the same pinned clang/lld/ldid
as r2). `tour/make-runtime-record.py --helper-build` writes a runtime record pinning it (`runtime-r7`).

**First results from the Swift/Xcode batch (runtime-r6, before the foreground fixes).**
- *HelloStoryboard (Xcode 16.4)* renders: storyboard scene, xib card, and the gold background from the
  `Brand` colour set in `Assets.car`, so compiled nibs, storyboards and asset catalogs all load on iOS 14.
  The iOS-beta "update available" alert sat on top, because bring-up mistook the gold app for wallpaper.
- *HelloAsync* stayed on the lock screen: `session.sh`'s single unlock swipe did not take.
- *NetNewsWire 6.0* installed with its real icon on Home page 2; the launcher's opens were refused while
  the device was locked (`FBSOpenApplicationErrorDomain` 7, "device is locked") and accepted at attempt 21
  after unlock, but the app was not in front afterwards (most likely a crash at start; no crash text reaches
  the serial console). Re-run queued with the icon reopen.
- *Notes Demo* (Linux-built, never run before) now runs in the foreground: "Notes Demo, Launches: 1 |
  Notes: 0", text field and buttons.

**Bring-up for imported apps, fixed three ways** (`tour/bringup.py`, `BRINGUP_NO_HOME=1`):
detect alerts by shape (a white body across mid-screen plus blue button text on the button row) rather
than by background colour; detect the lock screen by its dark torch and camera buttons and retry the
unlock; then press Home, go to page 2 and tap the app's icon (`BRINGUP_ICON`, default row 3 column 4 —
imports land right after "Imported Demo"). Checked on real frames: lock screen, an app under an alert,
Home, Home under a two-button alert.

**A queue mistake worth not repeating:** `RUNTIME` must be the record *file* (`runtime-r7/runtime.json`);
pointing it at the directory makes `prepare-import` fail instantly for every app. And `pkill -f PATTERN`
over ssh kills the ssh shell itself when the same command line contains the pattern; put such steps in a
script file.

**Apps built on Linux (JacobFV/ios-linux-toolchain: swift.org Swift 6.1.2 + the iPhoneOS 18.5 SDK +
ld64.lld-18, ldid-signed), on runtime-r7.**
- *HelloSwiftUI (Linux build)* renders fully: navigation title, grouped list (Controls / Drawing /
  Animation) and the About section. **A SwiftUI app compiled and linked on Linux runs on iOS 14 in the
  emulator.** The Xcode build of the same fixture also loads and stays running (process alive, earlier
  batch), but neither of its two runs got its screen captured (Home on the first; the second overshot to
  the App Library — Home returns to the last page shown, so bring-up now presses Home twice). So "same
  behaviour" is shown at the process level, not yet pixel for pixel.
- *swift-2048 (Linux build)* launches and draws its "Start Game" screen; the display then froze (the known
  compositor freeze: captures kept arriving, the status-bar clock stopped), so the taps and swipes that
  followed were delivered but never drawn. Re-run queued.
- *SwiftUIKit (Linux build)* and *Clendar (Linux build)* install with their real icons on page 2, and
  their opens are accepted after unlock, but both ended on Home. SwiftUIKit left a crash report
  (`SwiftUI Kit iOS-…ips`) before crash dumping existed; Clendar left none (slow start or a launch
  watchdog kill are both possible). Re-runs will print crash text.
- **Crash text now reaches the console.** The launch wrapper's root child prints any new CrashReporter
  `.ips` (first 32 KiB) between `INFERNO_APP_CRASH_BEGIN/END`; readiness's own prefixes stop at eight per
  boot and the MapKit snapshot service, Photos widgets, homed and maild use them up first.
- **A display defect worth noting:** one capture showed a band of corrupted pixels across the top of the
  App Library screen.

**Networking, attempt 1 failed for a silly reason:** `net-test.sh` began with
`ssh … 'sudo pkill -f ncm-bridge.py; …'`, and that pattern matched the ssh shell's own command line, so the
mode switch never ran and the phone stayed in configuration 4. Now `pkill -f "[n]cm-bridge"`, and the
script checks for "active config now 5". The USB companion also stops after `--seconds` (default 1800);
restart it with `usb-companion.py --resume-from OLD --output NEW --seconds 36000` (disk, packages and key
are kept).

## 2026-10-30: results of the overnight queue (runtime-r7, foreground bring-up, crash dumping)

| App | Built with | Result |
|---|---|---|
| Simon Tatham's Puzzles | Xcode (farm) | **runs**: full game list with artwork (Black Box, Bridges, Cube, Dominosa…) |
| vfr Reader | Xcode | **runs**: "Reader v2.8.8" |
| ACEDrawingView demo | Xcode | **runs**: drawing canvas with Undo/Redo/Clear and the Black/Pen/Image/Width/Alpha bar |
| HelloStoryboard | Xcode | **runs, clean**: storyboard, xib card ("Loaded from CardView.xib"), Assets.car colour |
| HelloSwiftUI / HelloSPM | **Linux** | **run**: SwiftUI list screen (SPM build too) |
| HelloMixed | **Linux** | **runs**: "Built on Linux — Objective-C says: 0 taps" (Swift + ObjC bridging) |
| HelloAsync | **Linux** | **runs**: "Swift Concurrency on iOS 14" (embedded `libswift_Concurrency.dylib`) |
| swift-2048 | **Linux** | **runs** to "Start Game" (twice); gameplay not yet recorded (the first run froze) |
| Tipulator | Xcode | crashes at start: `EXC_CRASH (SIGABRT)` through `libc++abi` — an uncaught exception |
| NetNewsWire 6.0 | Xcode | crashes at start: `EXC_BREAKPOINT (SIGTRAP)` in its own code — a Swift trap (likely a missing App Group container) |
| SwiftUIKit, Clendar | **Linux** | install, open accepted, end on Home; re-runs with crash text queued |
| jot (JotDemo) | Xcode | rejected at `prepare-import` (to investigate: probably its embedded Pods frameworks) |

**Networking, attempt 2.** The guest half works: the launch wrapper's root child logged
`INFERNO_NET_CONFIGURED if=en0 addr=0 route=0 publish=0` (address, default route and configd State keys
all set without error). The host half stopped short: `SET_MODE 3` was accepted (mode bytes 5,3,3) but
`set_configuration(5)` failed with **EBUSY**, because usbmuxd inside the companion holds the usbmux
interface. `net-test.sh` now stops usbmuxd and retries the selection (attempt 3 queued).
