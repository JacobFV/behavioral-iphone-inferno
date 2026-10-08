# Repeat the installed iOS owned-app journey

This procedure uses the existing verified iOS14 beta5 profile and the current
frozen from50-sample-1 disk tuple described below. It requires those external artifacts;
the repository does not contain Apple binaries or a distributable iOS image.
This is TCG with simulated SEP and the upstream direct-kernel patches.

The historical baseline used stage50 with app22, launcher22, readiness54 and
HID54, and emulator SHA256
`e3da84b179ce328e06a0f917aabb8e4d80c8a4cf64701212464831a270e1741e`.
Its retained evidence remains separate from current diagnostic runs.

## Current freeze investigation

The historical baseline above records the original journey. Current diagnostic
runs49 onward use frozen `disk-preparation-55/report.json`, app22/launcher22/
readiness54/HID55. Runs49–58 used emulator SHA256
`670caae5e8b86dbd07968b053ce0667328cce648935cefb8649357400f9c8e59`
from source09811d4d1d. Run59 adds the reviewed status-read diagnostic with binary
`f088a8c99437afaa9da220ee2f2e2a09f4dbf5b8638e897ec01c670c5273a7b7`
from build source2f29037290. The guest base remains unchanged. Its
three immutable backing ancestors and exact ctime-revalidation sidecars must
remain at their recorded paths. Never chmod an already-read-only ancestor;
ctime is part of the verified identity. See NEXT_SESSION.md for those identities.

Runs61–64 returned to the preserved original stage50/HID54 state. Run61 passed;
62–64 reproduced the persistent freeze. Those guests do not support SAMPLE.
The latest diagnostic build0889 adds exposed x21 to the existing ninth event;
interpret its ready bit only at the independently mapped interrupt-handler
caller. Run64 had that bit set while drawing submissions stopped. Runs65 onward use `disk-preparation-from50-sample-1/report.json`, a new branch
from a logically verified flattening of original50 with HID55. Actual recovery
readbacks and disk verification are retained in commits4dd630dc85 and67adbad5a7.
Recovery also changes filesystem/NVRAM state, so this is not an isolated HID
comparison. Never use a failed forensic attempt as a backing source.

HID55 supports two explicit original-tool samples per boot. On a genuine tap
with a persistently stale counter0, preserve continuous observation and let the
bounded display trace disable. Before Home or reopen, sample BACKBOARDD then
SPRINGBOARD once each, with the exact current boot UUID:

```sh
companion/run owned-control --report "$attempt" --output "$attempt/sample-backboardd-001" \
  sample --boot-uuid EXACT-CURRENT-GUEST-BOOT-UUID --target BACKBOARDD
# Wait for this request's actual END or FAILED record before the next request.
companion/run owned-control --report "$attempt" --output "$attempt/sample-springboard-001" \
  sample --boot-uuid EXACT-CURRENT-GUEST-BOOT-UUID --target SPRINGBOARD
```

Host acceptance does not establish a complete sample. Reconstruct each response
with [sample-result](SAMPLE_RESULT.md), inspect the actual text, and verify that
UUIDs and image slides come from this boot before offline symbol mapping.
Run49's two complete twenty-stackshot reports are the healthy comparison.
Sampling perturbs timing and does not itself explain or fix the freeze.
See [SAMPLE_CONTROL.md](native-probe/SAMPLE_CONTROL.md) for fixed targets,
identity checks, output bounds and the original tool's limitations.

## Bounded kernel diagnostic for a confirmed freeze

Run68 established actual production coverage of the two pinned SwapWait PCs
in a separate healthy Clock calibration. Its evidence is in
`evidence/swapwait-cpu-68-healthy-actual/`; interpretation limits and the next
failure protocol are in `evidence/swapwait-next-failure-plan/plan.json`.
The intermittent display freeze remains unresolved.

For the current diagnostic attempt, add `--swapwait-cpu-diagnostic` to the boot
command below. This sets the fixed address filter but leaves CPU logging off.
After a genuine tap and persistent unchanged reviewed frames, wait for all nine
ADP trace events to disable. Preserve continuous no-input VNC observation across
one window and restoration:

```sh
companion/run control --report "$attempt" swapwait-cpu-window --arguments '{"seconds":1}'
```

The runner checks the pinned binary/kernel, same-boot zero kernel slide and
nonoverlap with display traces. Inspect actual enable/restore acknowledgements
and byte offsets in `swapwait-cpu-control.jsonl`, then parse the retained log:

```sh
python3 companion/evidence/swapwait-cpu-parser/parse.py \
  --input "$attempt/guest-errors.log" --mode kernel-zero-slide \
  --output "$attempt/cpu-failure-parsed-001.json"
```

Review frames after restoration before interpreting a failed state. If rendering
resumes, record it as recovery during an intervention. Do not send a second tap,
Home or OPEN before preserving the failure evidence. Snapshots have no thread or
process identity and cannot be paired as calls. Healthy68 contained both pending
and successful return snapshots, with nonmonotonic token observations even for
the same client value. Global `nochain` changes scheduling; this is not a
performance measurement. Missing snapshots are inconclusive, not proof of no wait.

### Fixed decision-site profile

The opt-in `--swapwait-cpu-profile pending-equality` selects five reviewed
instruction sites instead of the baseline pair. It still requires
`--swapwait-cpu-diagnostic`; CPU logging remains disabled until the explicit
bounded window above. Before enabling, the runner verifies that all nine display
trace events are disabled. The same binary, kernel and zero-slide guards apply.

Parse its retained log with:

```sh
python3 companion/pending-equality-result.py \
  --input "$attempt/guest-errors.log" \
  --output "$attempt/pending-equality-parsed.json"
```

The output separates accepted modes, positive token-equality comparisons,
matching-request local values and final return statuses. They are independent
snapshot populations: do not pair them, subtract their counts, or propagate a
mode to another snapshot. `pipeline_bf4_token` names a field offset, not proof of
completion or safe reuse. Missing sites do not prove absent branches. Inspect
unknown/malformed records and semantic violations before interpreting results.
Owned relocated fixture coverage and cleanup passed. Healthy run84 then captured
all five original-kernel sites during an advancing Clock stopwatch:786 complete
snapshots with no unknown PCs or semantic violations. It included mode0, positive
equality, both matching-local values, and pending/successful returns. Those
independent populations are a healthy calibration, not failed-state coverage;
equality or a pending return alone cannot diagnose a freeze. See
`evidence/pending-equality-84-healthy-actual/`.

## Start one disposable guest

Run from the repository root. Choose a **new** output directory for every attempt.
The base report and all its backing dependencies must remain at their recorded
paths, read-only, with unchanged hashes. Do not point `--root-image` at a qcow2
leaf or add another staging layer above stage55.

```sh
attempt="$PWD/.local-build/reports/app-boot-NEW"
profile="$HOME/.local/share/inferno/images/ios14b5/verified-profile/profile.json"
base="$PWD/.local-build/reports/disk-preparation-from50-sample-1/report.json"
companion/run boot --profile "$profile" --output "$attempt" --seconds 7200 \
  --overlay-base-report "$base" --disk-boot --launchd-unsecure-cache \
  --guest-errors --capture-interval 30 --probe-journey --control-mailbox \
  --touch-trace-startup --touch-trace-seconds 900 \
  --guest-hid-serial --probe-keep-running
```

For a bounded journey requiring continuous display refresh, explicitly add
`--headless-refresh-seconds 300`. It starts one no-input observer after `cont`,
using only the runner's private Unix VNC socket. The default remains disabled.
It does not restart after expiry. Review actual connection/frame/closure times
in `headless-refresh/lifecycle.json`; a 300-second phase is not coverage of a
7200-second boot. The runner records observer CPU/RSS separately, and stops its
own child during cleanup. Early normal runner shutdown leaves the requested
observer phase incomplete but preserves its actual coverage interval. Lifecycle
failure is reported as an attempt error. This is an active display workload,
not a passive screenshot option or a fix for missing rendering submissions.

This process stays attached until normal completion. Use a separate shell for
the following operations. The runner creates private Unix endpoints and owns the
only QMP connection. Use its mailbox, never a second QMP client. Read the VNC
socket from the `-vnc unix:...` entry in the attempt's `command.json`.

## Observe, then issue one action

```sh
companion/run observe --socket /actual/private/vnc.sock \
  --output "$attempt/view-001"
companion/run control --report "$attempt" probe-status
```

Review `settled.png`. The initial frame may precede a new render. Capture-only
VNC uses a private socket and opens no user-display window. A connected client
can stimulate guest rendering; record whether it was present during measurements.

The tracked `owned-control` command replaces the temporary gesture/OPEN scripts.
Each invocation generates a fresh request ID, saves the request before submitting
it, and retains stdout, stderr, source hashes and submission times in a new
directory. It sends exactly one action and never retries. A host acceptance or
guest ACK alone does not establish that the intended UI changed.

After reviewing the current screen, choose only the applicable action:

```sh
# Lock-screen upward gesture; inspect the next frame before another action.
companion/run owned-control --report "$attempt" --output "$attempt/unlock-001" \
  swipe 16384 32270 16384 9145 --duration-ms 1500

# Close the beta alert only if that alert is currently visible.
companion/run owned-control --report "$attempt" --output "$attempt/alert-001" \
  tap 16384 18560 --duration-ms 150
```

Previous attempts needed two separately reviewed unlock gestures. Do not blindly
replay the list. Every observation and action output directory must be new.

## Complete the counter journey

Review unobstructed counter0 and the actual current-boot appearance event in
`serial.log`. Then explicitly capture the before frame, send one counter tap,
observe and review counter1, and explicitly capture the after frame:

```sh
companion/run control --report "$attempt" probe-capture-before
companion/run owned-control --report "$attempt" --output "$attempt/counter-001" \
  tap 16384 20316 --duration-ms 150
companion/run observe --socket /actual/private/vnc.sock --output "$attempt/view-002"
# After reviewing counter1:
companion/run control --report "$attempt" probe-capture-after
companion/run control --report "$attempt" probe-status
```

The report must show strict completion, with the genuine tap event and both QMP
capture hashes. Also review the actual QMP pixels. The keepalive flag leaves the
guest running for additional observations. Without it, strict completion ends
the attempt. Live `report.json` is an initial snapshot; query `probe-status` for
current state.

If a genuine tap is logged but the frame remains at0, leave the after capture
pending and retain the mismatch. Boot41 exposed this failure even with continuous
VNC observation; ordinary Home/reopen produced lifecycle events but did not
restore drawing. A successful callback or lifecycle parser is insufficient.
New runners support this fixed read-only diagnostic through the same mailbox:

```sh
companion/run control --report "$attempt" query-display-registers
```

It reads18 audited, nonconsuming display registers and retains the actual QMP
responses in the control transcript. Reads are sequential, not atomic, and do
not include framebuffer memory. Older running processes do not acquire new
commands merely because the checkout has changed. A register snapshot alone
does not establish the cause of a rendering failure.

For the current diagnostic emulator built from09811d4d1d, a bounded trace
can record submission, drawing and interrupt activity around a reviewed action:

```sh
companion/run control --report "$attempt" trace-display-window \
  --arguments '{"seconds":60}'
```

The fixed events are disabled by default. The window accepts integer1..60
seconds and rejects overlapping windows. The sole QMP owner disables them when
its polling loop reaches the deadline and again during cleanup; this is a
cooperative deadline, not a hard real-time limit. Inspect
`display-trace-control.jsonl` and the raw emulator trace for actual enable/disable
and device activity. Tracing can affect timing. Actual firmware-free validation
in `evidence/display-trace-build-control` proves control behavior only, not iOS
rendering. A healthy traced journey does not resolve the retained41 failure.

For a diagnostic action, add `--trace-checkpoints` before the `owned-control`
action subcommand. This records the fixed trace log's file identity and visible
size immediately around that single submission. After reviewing the resulting
frame, record another boundary without sending input:

```sh
companion/run display-trace-checkpoint --report "$attempt" \
  --output "$attempt/trace-after-review.json"
```

Checkpoint outputs must be new files. These are host file-visible boundaries;
buffering prevents exact device-event timestamps or attribution of every draw
to the tap. Match inode/device and retain the final raw log when examining byte
intervals. The43 trace has a documented pipe-index labeling defect; builds after
9cadee702b pass explicit pipe labels without changing emulation behavior.

After actual44 reproduced the stall, source09811d4d1d added two diagnostic events
for unimplemented main/pipe/blend register accesses and implemented pipe
configuration writes. The event set now has seven members. Start with a10-second
window to inspect volume: polling can produce many records, and the bound is by
time rather than bytes. Offsets are local to the named block after existing
shadow-alias normalization. Read events record the unchanged zero return value;
write events record the incoming value, not implementation of that register.

The later source change `bfcc434c20` adds an eighth event,
`apple_adp_status_read`, for the exact value returned by known INT_STATUS reads
at normalized offset0x45818. It changes no register state. Rebuild the emulator
before using that host trace set: the seven-event670 binary does not provide
this new event. Begin actual volume assessment with a10-second window. Fixed
HMP/QMP register queries use the same read path; avoid them within the window,
or preserve their provenance and do not attribute every read to the guest.
The original seven-event records remain valid evidence of their own binary.
The new diagnostic's build and actual execution status are in NEXT_SESSION.md.

The later source change `ec40c73c79` adds a ninth default-off event,
`apple_adp_read_caller`, only for existing reads at normalized offsets0x45004,
0x50184 and0x58184. It records CPU presence and exposed AArch64 PC/x30 without
synchronization, guest-memory reads or register writes. PC may reflect a
translation-block entry; neither address alone proves the exact executed call
site. Correlate with the same attempt's kernel slide and audited original code,
retaining unknown callers. The evidence parser under
`evidence/original-adp-fifo-error-path/correlate-callers.py` requires explicit
trace, stderr, original-kernel and new output paths. Never use another boot's
slide. Actual build/control and guest emission status are in NEXT_SESSION.md.

The archived670 and f088 binaries expose seven and eight events respectively.
Use their matching isolated host controller for full windows; a new controller
must reject unsupported events and clean up any events it already enabled.
A firmware-free control check has no display device and does not prove actual
caller attribution. Run62's seven-event failure remains valid independently of
this later diagnostic.

## Warm resume and timing

Use `observe --home-button` with a new output directory. It sends the emulator's
existing F6→SMC Menu press/release. Review SpringBoard Home and the actual owned
app background event before requesting OPEN. Supply the current guest boot UUID
from its raw event records, never a UUID copied from a previous run.

```sh
companion/run owned-control --report "$attempt" --output "$attempt/open-001" \
  open --boot-uuid EXACT-CURRENT-GUEST-BOOT-UUID
companion/run warm-timing --report "$attempt" --request-id ID-FROM-request.json \
  --output "$attempt/warm-001.json"
companion/run launch-timing --report "$attempt" --output "$attempt/initial-timing.json"
```

Review the returned counter1 separately. Warm timing requires actual
background→OPEN→foreground/active records and the same original process
incarnation. These are guest lifecycle intervals, not frame presentation times.
The initial-launch parser deliberately rejects multiple process incarnations;
derive and preserve its result before a fresh-process experiment.

Boot38's fresh-process evidence is in `evidence/process-launch-38-actual` and
`evidence/process-launch-38-visual`. That procedure used ordinary AppSwitcher
dismissal, a complete original process-list absence snapshot captured before
OPEN, and distinct original kernel process identities. It did not clear caches.
Use `process-launch-timing --help` for its separate capture/derive commands.

For a fresh-process extension of a completed strict journey without per-marker
arrival records, retain a raw strict prefix **immediately after** the successful
`probe-capture-after` response and before App Switcher, dismissal or OPEN. Do not
create a retrospective checkpoint after the new launch. Use new filenames:

```sh
python3 - "$attempt" <<'PY'
from pathlib import Path
import hashlib, json, os, sys, time
folder = Path(sys.argv[1]).resolve()
started = time.time()
raw = (folder / 'serial.log').read_bytes()
prefix = raw[:raw.rfind(b'\n') + 1]
assert prefix
path = folder / 'strict-completed.serial-prefix.log'
with path.open('xb') as stream:
    stream.write(prefix)
    stream.flush()
    os.fsync(stream.fileno())
manifest = {
    'serial_prefix_path': str(path),
    'serial_prefix_bytes': len(prefix),
    'serial_prefix_sha256': hashlib.sha256(prefix).hexdigest(),
    'read_started_host_epoch': started,
    'captured_host_epoch': time.time(),
}
with (folder / 'strict-completed-prefix.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
PY
```

Keep both original files. After reviewing the owned App Switcher card, dismiss it
with one explicit gesture, then retain a **complete** original process listing
that follows that gesture and shows both old PID and exact executable absent.
Run `process-launch-timing capture-absence` before issuing OPEN; select the actual
completed readiness interval rather than assuming that its nominal time elapsed.
Only then request OPEN with the current boot UUID. Derive timing with the old
and new PIDs, that named request and the absence manifest, and review the new
counter0 separately. This proves an observed new process, not cleared caches.

After normal shutdown, add `--strict-prefix "$attempt/strict-completed-prefix.json"`
to `verify-journey`. The verifier requires an exact prefix of the final log,
capture-completion ordering, checkpoint-before-OPEN ordering and paired event
provenance. A checkpoint does not supply per-marker arrival times or override
contradictory recorded arrivals. Actual56 validates this workflow; its original
strictPID261 and laterPID375 remain separately identified.

## Resources and normal completion

```sh
companion/run resources --report "$attempt" --output "$attempt/resources-001" \
  --seconds 60 --interval 1
companion/run control --report "$attempt" finish-run
```

`finish-run` requires strict completion and keepalive. It requests ordinary QMP
cleanup. Wait for the boot process to exit, then inspect the final report,
serial/control/QMP logs, stopped disk hashes and unchanged backing dependencies.
An incomplete or interrupted attempt stays incomplete; preserve its failure.

```sh
companion/run verify-journey --report "$attempt" --output "$attempt/verified-journey.json"
```

The verifier matches raw guest events, explicit controls, serial input, actual
frame hashes and QMP capture/shutdown records. It does not classify screenshot
pixels; visual review remains separate. Without an optional host arrival
observer, chronology relies on the exact reviewed runner capture gates plus
accepted commands, not independent serial-arrival timestamps. Unknown gate source
revisions fail rather than silently inheriting that interpretation.

For a normally stopped attempt without an existing stopped manifest:

```sh
companion/run preserve-stopped --report "$attempt" \
  --output "$attempt/stopped-disk-hashes.json"
```

Both the manifest and its `stopped-disk-hashes-verification.json` sidecar must be
new files. This command checks actual QMP shutdown records, the seven stopped
namespaces and immutable backing ancestors. It neither freezes files nor launches
guests. Keep every backing layer. Linux `/proc` permission gaps are recorded;
descriptor checks cover readable processes at verification time, not a host-wide
exclusive lock. Existing retained attempts can be rechecked using a different
new output filename without rewriting their original evidence.

For an explicitly failed attempt that nevertheless completed normal QMP cleanup,
`preserve-stopped --failed-attempt` records the attempt error and marks the root
`forensic_only:true`. The overlay loader rejects that manifest as a new backing
base. The flag cannot bypass emulator-exit, QMP-shutdown, disk or ancestor checks.
It does not convert the failed journey into a pass. Boot41 retains this scope.

For a specifically bounded two-guest experiment, start a second sibling from the
same base, with separate output/endpoints, and complete the reviewed journey in
each. Then close all VNC clients, send no input, and run:

```sh
companion/run density --report /absolute/first-attempt \
  --report /absolute/second-attempt --base-report "$base" --output /fresh/sample
```

This takes one common60-second window. CPU100% means one host logical core.
PSS apportions shared pages; RSS counts them repeatedly. The sum excludes other
host allocation and the runner. Both actual39/40 guests retained periodic30-second
QMP captures and startup900-second touch tracing: the recorded window is
instrumented foreground idle. The raw sample and independent recomputation are
in `evidence/density-39-40-actual`; reviewed surrounding images are in
`evidence/density-39-40-visual`. Neither these samples nor the successful fixture
establish maximum density, cost, native-device speed or general app compatibility.

## Display observation cadence found in run53

A QMP screendump completion does not establish completion of the guest's next
render submission. With no VNC client, the VNC timer skips display refresh;
periodic QMP requests can leave animation frames visibly behind wall time.
Run53 confirmed this with the original Clock stopwatch, then advancing frames
under a continuous headless VNC observer. Record observer connection intervals
alongside measurements. The observer changes the display workload and its host
CPU is outside whole-QEMU resource samples. Do not infer an active visual frame
rate from sparse QMP captures. This does not explain away persistent44/47, where
submissions stopped despite a continuous VNC client. See the actual53 trace,
source-analysis and resource evidence directories.

### Explicit new-process recovery audit

When an initial process emitted only a validated main marker and a later explicit
OPEN created the process used for the strict captures, `verify-journey` supports
`--recovery-open-request RID`. It requires the exact host/serial request, accepted
original callback, original process identity and a new five-hook incarnation
between the request and callback, with main/delegate/window hooks in order.
Any prior main-only marker must precede the named guest OPEN request. It retains prior launches and all rejection
records, validates every lifecycle record, and still checks the actual tap and
QMP captures. A prior appeared/tap marker is rejected without historical arrival
proof; this mode does not invent a prefix.

The result is `verified-recovered-journey` with `whole_boot_verified: false`, never
whole-boot success. Default verification and timing parsers remain unchanged.
See [actual run67 replay and limits](evidence/recovery-journey-67-replay/README.md).
