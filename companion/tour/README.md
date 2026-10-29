# App tour: many apps on one fresh device, recorded

Drives a fresh, setup-complete installed boot through a list of apps and records
the emulator display at 1 Hz. It reuses only tracked entry points: `boot.py`,
`owned-control` (one HID gesture per request), `observe` (capture and the F6 Home
button) and `qmp_control.py finish-observation` (normal stop).

Getting a setup-complete base (2026-10-29, second host):

1. Run the fresh chain to `fresh-runtime.json`, then `boot-fresh.py`.
2. Answer Setup Assistant with ordinary gestures. It needs ~25; the owned HID helper
   now allows 2048 per boot (`INFERNO_HID_MAX_REQUESTS`). The old 32 is why
   fresh-boot-6 stalled at "Welcome to iPhone".
3. "Welcome to iPhone" does not visibly advance, but setup completion is already
   persisted there. End the boot with `finish-observation`, run `preserve-stopped.py`,
   clear the write bits on its `disks/*`, and use its `report.json` as `TOUR_BASE`.
   Every later boot from it starts at the lock screen.

Then `tour-cycle.sh PLAN FIRST_BOOT_NUMBER [SKIP]`:

- boots from the base, waits for the lock screen, unlocks, and `bringup.py` dismisses
  the beta-update and "Finish Setting Up" alerts (detected by the dimmed background);
- runs `../app-tour.py` with the plan; `--freeze-dir` stops it (exit 3) when the
  status-bar clock has not changed across two apps, which is the documented
  compositor freeze (`../FREEZE_HYPOTHESES.md`);
- stops that boot normally and boots again, resuming one app before the freeze.

`ATTACH=1` reuses an already running, already unlocked boot for the first round.
Plans are JSON lists of apps with taps/swipes in frame pixels (832x1792), so new
apps, including imported ones, are new entries. `review.py` makes contact sheets,
`segments.py` maps recorded frames to apps, and `build_tour.py` assembles a video
from those frames only (scaled, never edited).

Expect a freeze every 5-16 apps; each restart costs ~12 minutes to the lock screen.
