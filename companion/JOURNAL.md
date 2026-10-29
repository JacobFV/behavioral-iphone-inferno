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
