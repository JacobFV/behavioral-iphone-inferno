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
