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
