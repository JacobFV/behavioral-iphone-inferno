# Intermittent display freeze: ranked root-cause hypotheses

Offline analysis of retained evidence only (no VM, no new execution). Sources:
`hw/display/apple_displaypipe_v4.c`, `companion/evidence/` (display-stall-44/47,
display-completion-state-audit, adp-caller-63/x21-64/65/66/68, original-adp-*,
original-iomfb-swapwait-path, swapwait-cpu-76/82/84, token-ordering-limit-89,
compositor-token-selection-84, reproduction-cadence-65-69), PROGRESS.md and
NEXT_SESSION.md. Original-kernel disassembly under
`~/.local/share/inferno/native-probe/iomfb-swapwait-inspection/` was read only.
Nothing here is an execution result; every item is a hypothesis.

Note on run labels: this repo's records classify run 84 as a healthy Clock
calibration (pending equality 192/200, tokens 468..472 advancing) and run 74 as
the imported-fixture freeze. Failures with recorded evidence: 41, 44, 47, 62-65,
74, 76, 82.

## What the evidence fixes (facts)

1. The display-pipe model's interrupt/draw chain is intact through the *last*
   submission in every failing run. Failed 44/47 and healthy 49/53/57 contain
   complete submit -> BH enter -> BH exit -> guest W1C chains (audit.py). In run 65
   the final submit (0x1a00) is followed by the same ready/W1C, 0x45004 read
   (x21=0x400) and the single main 0x46134 + blend 0x3038 read pair that follows
   every other submit (counted per log: 65 16/14/15, 66 43/43/43, 68 49/48/48,
   46 39/40/40 submits/0x46134/0x3038). After that: 38 more ready+W1C pairs, 33+
   0x45004 reads with x21=0x400, **zero** config writes, **zero** submits.
2. In the freeze the guest interrupt handler still reaches its ready gate (runs
   63/64/65: all x21=0x400 samples, matching status/W1C). Wait site state
   (run 76: 228/228 entries token 293, 228/228 returns 0xe00002d5; run 82: 183/183
   null active, requested 253 == pipeline+0xbf4 == 253, no queued request).
3. backboardd samples (65/74/76/82): 5/21 or 11-ish in display_timer_callback ->
   vsync_callback -> render_for_time -> can_update_ -> kern_SwapWait / usleep
   retry; SpringBoard main is 20/20 idle in runloop. App lifecycle shows the tap
   was handled; only compositor output is stuck.
4. Pending status and token==bf4 equality are also common in healthy runs
   (84: 195/199 returns pending, 192 equality snapshots). The failure signature is
   **stationary** token, null active, empty queue, and no new SwapBegin/submit - not
   the pending status itself.
5. Submit register value is `0x1000 | (counter << 8)`; it wraps (0x1f00 -> 0x1000)
   in healthy runs. Failures stop at 0x1e00 (44, 64), 0x1200 (47), 0x1600 (63),
   0x1a00 (65): no correlation with counter value.
6. 62-65 reproduced 4/4 from the same stage50 disk state with different host
   timing, while 66-73 and 77-94 on other states/paths passed. Run 71/72 matched
   the ~10 s setup->counter gap and stayed healthy. Together: more logical than
   racy, but cadence alone is not sufficient.

## Ranked hypotheses

### H1 (most supported): guest scanout-token bookkeeping desync -> compositor self-deadlock

can_update_ selects a record (start `self+0x29c`, skipping `self+0x2a0`), then
calls non-blocking SwapWait(token). Mode 0 returns pending while token ==
`pipeline+0xbf4` (or equals the active/queued request). With nothing in flight,
equality can only resolve when a *new* swap completes, but can_update_ gates the
very render that would submit it. Healthy runs avoid this because the selected
record is not the one that equals bf4.

Sub-hypothesis H1a (concrete trigger): `swap_complete_gated` copies request+0x22c
into pipeline+0xbf4 only if `request+0x244 == 0 || == 0xf`
(0xfffffff0096f0cfc..0d28 in complete-gated.txt); otherwise the active request is
still cleared (0xe58..0e60) and waiters woken but bf4 is not updated. If a swap
whose +0x244 is outside {0,0xf} completes, the compositor believes record B is
displayed (index excluded) while the kernel retains A; next selection picks A,
token A == bf4, active null -> permanent pending. This matches 82 exactly
(active null, requested == bf4) and the fixed token in 76.

For: items 2-4 above; wait-site populations; stack samples; deterministic
reproduction from one disk state (item 6); static code path exists and is
consistent with token-ordering-limit-89 ("equality compatible with retained bf4
after active removal") and the 84 token-selection "index mismatch" boundary.
Against / unknown: writer of request+0x244 not in retained disassembly ranges;
no run captured record index/2a0 or W25 token association; equality+null-active
is also what a *benign* idle wait looks like, so it may be a consequence rather
than the cause; no failed-state value of +0x244 exists.

Cheapest discriminating experiment: zero-VM first - locate stores to
`request+0x244` in the original kernel IOMFB text (existing llvm-objdump-18 pin,
read-only) to learn what sets it (swap kind/flags vs. hardware readback). Then
one 1 s window on a **healthy** Clock/stopwatch or tap journey (no freeze needed)
with a new fixed profile adding PC 0xfffffff0096f0d00 (W9 = request+0x244) and
0xfffffff0096f0d28 (executed only on copy), same `--swapwait-cpu-diagnostic`
guards, ADP traces off. Expected if H1a: some completions hit d00 with W9 not in
{0,0xf} and no d28 hit; healthy-only runs with all W9 in {0,0xf} weaken H1a (not
exclude: needs the tap-time swap). Requires a reviewed profile addition in
`companion/qmp_control.py` SWAPWAIT_PROFILES plus TB-reachability review.

### H2: emulator timing realism: zero-latency FRAME_PROCESSED racing guest SwapEnd bookkeeping across vCPUs

`submit` -> `qemu_bh_schedule` -> BH draws and ORs FRAME_PROCESSED on the next
main-loop iteration (microseconds), IRQ0 recomputed, AIC delivers to either vCPU
(callers alternate cpu_index 0/1 in the logs; `-smp 2`, TCG). Real hardware
completes a frame at least one scanout period later. If completion is serviced by
the other vCPU before the submitter finishes post-submit state (request state
fields like +0x244/+0x264, ring token store, userclient return), kernel
state-machine branches taken in the real driver never occur - and that could feed
H1a. OUTPUT_READY is independent: raised from host `gfx_update` (UI refresh), not
from a submit.

For: model has no latency; intermittent; tap changes timing; cross-CPU delivery.
Against: failing last chains have the identical ordering to healthy chains (audit:
no second submit before clear, no ready/processed inversions in windows); 4/4
reproduction from one state argues for determinism; tracing changes timing yet
failures reproduce with traces on (44,47,63-65) and off (62,76,82).

Cheapest experiment: no model change - run the failing disk state (stage50
sequence that failed 62-65) with TCG single-threaded (`-accel tcg,thread=single`,
needs a one-line boot.py option; `-smp 1` is a second variant). Expected: if H2,
the freeze rate on the same replay drops sharply (needs >= 5 replays since it
reproduced 4/4); if H1a is deterministic logic, it still freezes.

### H3: never-raised enabled interrupt sources / missing hardware events change the swap path

Guest enables 0xc0180c08 (bits 3, 10, 11, 19, 20, 30, 31) but the model only ever
sets bits 10 and 20; all other registers read by the handler (0x46150.. 0x460b4..
0x460d8, 0x4617c/0x46180, 0x46178, 0x3038, 0x46134, 0x97bc) return constant 0 via
the unknown-MMIO path. A completion ID/timestamp or frame counter that is always
0 could steer swap_request_complete's equal-ID vs unequal-ID branch
(0xfffffff0097b8bac..cdc vs ce4..d88: equal ID + property false returns without
completing; unequal ID reaches the bf4-copy path).

For: frame_done/ready path reads these once per submit and they are constant;
explains determinism. Against: healthy runs advance bf4 with the same constant
reads; pipeline+0x122c source not shown to be an MMIO read. Value of
the incrementing submit counter (item 5) may be the real ID source.

Cheapest experiment: static first - identify the producer of pipeline+0x122c and
`self+0x1bf8` (swap_request_complete arguments, 0xfffffff009745494..4a4). If it is
an MMIO value, the existing `apple_adp_unknown_mmio` trace plus a model returning
distinct per-frame values on 0x46134/0x46150 in a single boot is the test; if not,
discard.

### H4: host-UI-dependent OUTPUT_READY cadence

Ready is produced only when a console consumer triggers `gfx_update`
(documented in stopwatch-display-refresh-53-analysis). Not tied to submits (about
6 ready per submit in healthy 65/68). For: documented observer-dependent QMP
capture lag; Against: freeze logs show ready continuing at the same rate with
continuous VNC, and the handler consumes them. Treat as a *separate* artifact
(already addressed by the optional headless refresh observer), not the freeze
cause. Cheapest experiment: none needed beyond keeping a headless VNC observer on
during a replay; if the freeze persists with a continuously driven refresh, H4 is
excluded.

### H5 (largely excluded): lost/coalesced IRQ, BH, W1C or AIC masking

Single-bit status and one BH can coalesce, and AIC masks on IACK, but: complete
chains and acknowledgments are present up to and after the last submit (audit
5/5/12/42/14), ready/W1C pairs keep flowing, and the guest-side handler ran the
ready gate (x21=0x400). A lost submit is also excluded: there are no further
0x4602C writes at all (not bit12-filtered; unknown-MMIO shows no writes). Remaining
residue is a preceding untraced transition. Experiment (existing flags): the
ten-second ADP trace window already covers it; no new run needed.

## Emulator-side fix candidate

The evidence does **not** support claiming a display-pipe model defect: the model
completes every observed submission and the guest handler acknowledges it. The only
candidate consistent with the evidence (H2/H1a) is a default-off realism option,
to be A/B tested, not a fix claim:

- Add a device property (default off) that delays FRAME_PROCESSED from the
  submit BH to a QEMU_CLOCK_VIRTUAL timer of about one frame period
  (about 16.7 ms), still drawing in the BH, one completion per submit (count, not a
  bit, so back-to-back submits cannot coalesce). Keep the periodic gfx_update
  OUTPUT_READY. Gate by property so existing evidence stays reproducible.
- Validate with the same stage50 replay that failed 62-65 (>= 5 replays) before
  any default change; healthy runs must stay healthy.

If H1a is confirmed, the cause is a guest-driver state predicate keyed on a
request field, and an emulator-side change would have to come from learning what
sets request+0x244 (hardware readback vs. software), not from IRQ/vblank edits.
Do not fabricate completion or bypass the guard (AGENTS.md).

## Recommended order

1. Zero-VM: find request+0x244 / pipeline+0x122c producers in the original kernel
   (decides H1a vs H3 offline).
2. One healthy-run 1 s window with the two-PC complete-gate profile (H1a).
3. Single-thread-TCG replay of the stage50 failure sequence (H2).
