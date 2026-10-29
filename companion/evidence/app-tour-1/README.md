# app-tour-1: a fresh device through Setup Assistant and 21 stock apps (second host)

2026-10-29, `promaxgb10-4dfb` (machine-id `96ac3ff3…`). Raw outputs stay outside Git under that
host's `~/.local/share/inferno/app-import/` (`*-r6` stages, `fresh-boot-r6`, `tour-boot-1..10`).
`summary.json` lists stage result hashes, the setup boot and, per tour boot, the apps completed,
the freezes detected and the frames recorded. No Apple binaries or screenshots are tracked here.

## What ran

- The whole fresh chain from the IPSW alone: raw recovery, initial volumes, Data seed/verify/flatten,
  growth, SEP keybag and flatten, runtime inspection, renderer cache patch (original cache extracted
  and re-patched with the pinned InfernoFSPatcher; both full hashes matched the recorded values),
  runtime artifacts and the fresh-runtime stage. Every helper rebuilt byte-identical except the HID
  helper, whose bounds were raised (commit 2f03b87).
- `boot-fresh`: Setup Assistant answered with 37 acknowledged gestures to "Welcome to iPhone".
  The earlier 32-gesture HID budget is what stopped fresh-boot-6 there. The screen does not advance;
  setup completion is persisted, as in historical boots 22/23. `finish-observation` ended it normally.
- Ten tour boots from that stopped state, each reaching the lock screen. Unlocking opened the
  imported Linux-built demo; two taps moved its counter 0 -> 2.
- Two passes over the 23 apps on Home page 1 and the dock (`../../tour/plan-builtin-pass*.json`).
  Freezes stopped boots 3, 5, 6, 8 and 9 (status-bar clock unchanged across two apps); each restart
  resumed one app earlier.

## What the frames show (reviewed by eye)

Opened and used: Settings (General), Clock (World Clock, Alarm, running Stopwatch with a lap, Timer),
Notes (welcome, list, new empty note), Calendar and Photos ("What's New"), Books ("Get Started",
Reading Now offline), Health (welcome, "Set up Health Details"), Wallet, Home (welcome; adding a home
fails without iCloud), TV, News, Mail (account providers), Safari (Favorites), Messages, Music
("What's New"), Phone (keypad), FaceTime (Apple ID prompt), Weather (Cupertino page, no data),
App Store ("must connect to a Wi-Fi or cellular network").
Blank: Reminders, Podcasts. Quit to Home on launch: Maps, Stocks.

The 248 s video (`iphone-on-linux-app-tour.mp4`, sha256 `73e6e4920b18…`) is built from those
captures by `../../tour/make_cuts.py` and `build_tour.py`; frames are scaled, never edited.
It is published on jvboid.dev (iPhone on Linux).
