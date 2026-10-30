# Freeze experiment 2: a vblank on the guest's clock (pre-registered 2026-10-30)

Written before any trial ran; results are appended below the line.

## Why

Experiment 1's first trials froze in every arm (base, completion-delay, single-thread TCG), most of
them at the first or second app launch, with 6–7 emulators sharing the host. That is far earlier
than the ~45% per session seen with 2–3 emulators, so host load looks like a strong factor, and the
FRAME_PROCESSED timing knob did not visibly protect.

One display signal in the model *is* host-paced: OUTPUT_READY, which the guest treats as its frame
tick (backboardd's display_timer_callback → vsync_callback → render_for_time → can_update_). It is
raised only from `adp_v4_gfx_update`, the host console refresh, so its rate in guest time depends on
whether a VNC client is attached, QEMU's adaptive VNC refresh interval (30 ms up to 3 s when nothing
changes) and how fast the host runs the guest. Real hardware raises it every scanout, in step with
the guest's own clock.

## Hypothesis

H-vblank: the freeze is triggered by OUTPUT_READY arriving at a guest-time cadence that real hardware
never produces (irregular, bunched, or spaced seconds apart), so the compositor's swap bookkeeping
(H1/H1a) reaches its stuck state. Driving OUTPUT_READY from a QEMU_CLOCK_VIRTUAL timer every 16.67 ms
(guest time) should make the freeze rare, independent of host load.

## Arms (one experiment-2 binary; new properties are default off = old behaviour)

- **base**: no knobs.
- **vblank**: `-global apple-display-pipe-v4.vblank-ns=16666667` (OUTPUT_READY from the virtual
  timer; the host refresh no longer raises it).
- **vblank+complete**: as vblank, plus `complete-at-vblank=on` (each drawn frame's FRAME_PROCESSED is
  delivered on the next vblank tick, in order, one per submit).

## Workload, measurement and stopping

Same as experiment 1 (fresh boot from the setup-complete base, unlock, `plan-builtin-pass1.json`, 23
apps, freeze when the status strip is unchanged across two apps), 4 lanes, block-randomised order,
**8 trials per arm**. Run while host load is comparable to experiment 1's (4 experiment lanes plus at
most 2 other lanes); the lanes log start/stop so the overlap can be reported.

## Predictions and falsifiers

- base is expected to freeze in most trials at this load (≥ 5 of 8); if it freezes in ≤ 2 of 8, the
  load changed and the comparison is uninformative.
- **H-vblank supported** for an arm if it freezes in ≤ 1 of 8 while base freezes in ≥ 5 of 8
  (Fisher exact one-sided p ≈ 0.02). Then ≥ 10 further trials of that arm, at least 5 at lower
  load, before proposing any default change.
- **Falsified** for an arm if it freezes in ≥ 4 of 8, or breaks boot/display (no frames, boot
  failures, a black screen).
- Secondary: apps completed before the freeze, per arm; and for the vblank arms, whether animations
  (e.g. the Clock stopwatch) run at a plausible rate (a too-fast or too-slow vblank would show).

Unmeasured assumption, stated: 16.67 ms is the iPhone 11 panel's refresh. The device tree's
`display-timing-info` is hard-coded in the model and not checked against the real panel.

---

## Results

(appended after the trials)

**Ran 13:44–16:04 on 2026-10-30; 14 trials** (the user stopped the series at 14; 10 unrun trials are
listed in `~/inferno-chain/exp2/trials-unrun.txt`). Deviations, stated: n is 5/5/4 rather than 8 per
arm; and for part of the run three non-experiment lanes ran beside it (a vblank network tour, the
page-2 re-tour, a crash capture) where the plan allowed two. That extra load works against the vblank
arms, not for them.

| arm | frozen | completed | freeze rate | 95% CI (Clopper–Pearson) | apps done |
|---|---|---|---|---|---|
| base | 5 | 0 | 5/5 = 100% | 48–100% | 12, 3, 3, 3, 3 |
| vblank | 0 | 5 | 0/5 = 0% | 0–52% | 23 ×5 |
| vblank + complete-at-vblank | 0 | 4 | 0/4 = 0% | 0–60% | 23 ×4 |
| either vblank arm | 0 | 9 | 0/9 = 0% | 0–34% | |

Fisher exact, one-sided, against base: vblank p = 1/252 ≈ 0.004; vblank+complete p = 1/126 ≈ 0.008;
both vblank arms pooled p = 1/2002 ≈ 0.0005.

Checks that a "completed" really was a moving display (not a detector miss): in X-113-vblank the
status-bar clock advances 3:34 → 3:47 → 4:04 across the recording while apps open and draw (Books'
"Get Started" sheet, then Home). The vblank arms rendered normally throughout (Settings, Clock, Photos
etc.). Separately, a network tour on the vblank binary (`session-NetTour6vb`, not randomised, not
counted) ran its whole plan (Safari on two sites, App Store, News, Podcasts, TV, Weather, Books, Music,
Mail) without freezing, where network tours 2–4 on the stock binary had all frozen part-way.

**Verdict: H-vblank is SUPPORTED by the pre-registered rule** (base ≥ 5 frozen, arm ≤ 1 frozen):
raising OUTPUT_READY from a guest-clock 60 Hz timer instead of the host console refresh took the freeze
from 5/5 to 0/9 at a load where it otherwise happens in nearly every session. Delivering FRAME_PROCESSED
on the tick as well (complete-at-vblank) made no visible further difference; plain vblank is sufficient.

It is **not yet a default change.** The plan requires ≥ 10 further confirming sessions of the chosen
arm, at least 5 at low load (1–2 emulators), and those have not run. Also unchecked: whether
animations run at the right speed with a 16.67 ms guest-time tick (the Clock stopwatch is the obvious
test), and whether the host-console path still needs OUTPUT_READY for anything else.

What this says about the mechanism (a hypothesis, not tested here): the compositor's frame loop is
driven by OUTPUT_READY, and when that tick arrives at host-paced, irregular guest-time intervals the
swap bookkeeping can enter the stuck state documented in `FREEZE_HYPOTHESES.md` (H1/H1a). A guest-time
vblank keeps the tick regular. Host load made the old path worse, which is why the freeze rose from
~45% to ~100% of sessions as more emulators shared the host.
