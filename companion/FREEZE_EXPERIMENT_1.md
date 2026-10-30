# Freeze experiment 1: completion timing and vCPU threading (pre-registered 2026-10-30)

Question: does the intermittent compositor freeze (`FREEZE_HYPOTHESES.md`) depend on *when* the
display pipe signals FRAME_PROCESSED, or on two vCPUs servicing it concurrently?

Written before any trial ran. Results are appended below the line, never edited above it.

## Background

`hw/display/apple_displaypipe_v4.c` raises FRAME_PROCESSED in the same main-loop pass that draws a
submitted frame (`adp_v4_update_disp_bh`), microseconds after the guest's submit write. Real
hardware completes a frame no earlier than the next scanout. H2 in `FREEZE_HYPOTHESES.md` proposes
that a zero-latency completion, delivered to whichever vCPU takes the interrupt, can overtake the
submitting thread's bookkeeping, which would feed H1a's stuck-token deadlock. The tour logs since
2026-10-29 put the freeze at about 45% of sessions (15/34 on 2026-10-30).

## Arms (one experiment binary for all three, so the knob is the only difference)

The experiment binary is the pinned source revision f37ad49 plus one change: a `completion-delay-ns`
property on `apple-display-pipe-v4`, **default 0 = exactly the old behaviour**. With it set, the
draw still happens in the BH, but FRAME_PROCESSED is raised by a QEMU_CLOCK_VIRTUAL timer that many
ns later. Completions are counted, one per drawn submit, so the delay cannot merge two frames into
one interrupt.

- **base**: experiment binary, no knobs.
- **delay**: `-global apple-display-pipe-v4.completion-delay-ns=16666667` (one 60 Hz frame).
- **single**: `-accel tcg,thread=single` (both vCPUs on one host thread; H2's cross-vCPU race
  cannot happen).

## Workload and measurement

Each trial: one boot from the setup-complete base (`fresh-boot-r6`), the standard unlock and alert
bring-up (`session.sh`), then `plan-builtin-pass1.json` (23 built-in apps, page 1 and dock) from
index 0 with `app-tour.py --freeze-dir`. A freeze is declared when the status-bar strip is identical
across two consecutive apps (about two minutes of a stopped clock). Per trial: outcome (frozen /
completed / boot-failed / error), apps completed before the freeze. Trials run four at a time
(`exp-freeze.sh`, `INFERNO_ALLOW_CONCURRENT=1`) in block-randomised order so that every arm sees the
same mix of host load and lanes.

## Pre-registered predictions and falsifiers

- n = 8 trials per arm (24 total), analysed as frozen/completed (boot failures and errors excluded
  and reported).
- **H2 / delay supported** if the delay arm freezes in at most 1 of 8 while base freezes in at
  least 3 of 8 (Fisher exact one-sided p < 0.1 at that split), with ≥ 10 confirming trials to
  follow before any default change.
- **single supported** by the same rule for the single arm.
- **Falsified** for an arm if it freezes in ≥ 3 of 8 (no material reduction), or if it breaks
  the display (no frames, boot failures) — that also counts as a negative result.
- If base itself freezes in ≤ 1 of 8, the experiment is **uninformative** (workload too mild);
  report it and lengthen the plan rather than reading anything into the arms.
- Secondary: apps completed before freezing (a survival measure), reported per arm with no
  threshold.

Unmeasured assumptions, stated: the freeze detector's two-app window is the same for every arm;
the single-thread arm runs the guest slower, so it sees fewer guest events per wall-clock app,
which could lower its freeze rate for a reason unrelated to H2 — read a positive single result
with that in mind.

---

## Results

(appended after the trials)

**Ran 12:05–13:44 on 2026-10-30; stopped after 15 of 24 trials.** Deviation from the plan, stated: I
stopped handing out trials once every arm had met its pre-registered falsifier (≥ 3 of 8 frozen); the
9 unrun trials are in `~/inferno-chain/exp1/trials-unrun.txt`. In-flight trials were allowed to finish.

| arm | frozen | completed | error | apps done before the freeze (detector) |
|---|---|---|---|---|
| base | 5 | 0 | 0 | 3, 5, 7, 3, 6 |
| delay | 4 | 0 | 1 | 5, 5, 5, 3 |
| single | 5 | 0 | 0 | 3, 5, 4, 3, 11 |

The error (trial 11) was the harness, not the guest: the freeze detector opened a frame the recorder
was still writing (`UnidentifiedImageError`); fixed in `app-tour.py` the same afternoon.

**Verdict:** both hypotheses falsified at this load. Delivering FRAME_PROCESSED one frame later did not
reduce the freeze (4/4), and neither did removing cross-vCPU concurrency (5/5). Base froze 5 of 5, so
the experiment was informative. The detector fires up to two apps after the onset; the frames show the
display usually stopping at the *first or second* app launch, typically on a blank launch screen with
the clock stopped (e.g. trial 2: 16 captures over 160 s, all at 12:22).

**What it suggests:** with 6–7 emulators sharing the host, the freeze went from ~45% of sessions to
essentially every session, early. A host-load dependence points at something paced by host time.
Experiment 2 (`FREEZE_EXPERIMENT_2.md`) tests the one display signal the model paces by the host
console refresh: OUTPUT_READY.
