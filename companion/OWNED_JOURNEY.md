# Repeat the installed iOS owned-app journey

This procedure uses the existing verified iOS14 beta5 profile and frozen stage50
disk tuple. It requires those external artifacts; the repository does not contain
Apple binaries or a distributable iOS image. The actual baseline is app22,
launcher22, readiness54 and HID54 with emulator SHA256
`e3da84b179ce328e06a0f917aabb8e4d80c8a4cf64701212464831a270e1741e`.
This is TCG with simulated SEP and the upstream direct-kernel patches.

## Start one disposable guest

Run from the repository root. Choose a **new** output directory for every attempt.
The base report and all its backing dependencies must remain at their recorded
paths, read-only, with unchanged hashes. Do not point `--root-image` at a qcow2
leaf or add another staging layer above stage50.

```sh
attempt="$PWD/.local-build/reports/app-boot-NEW"
profile="$HOME/.local/share/inferno/images/ios14b5/verified-profile/profile.json"
base="$PWD/.local-build/reports/disk-preparation-50/report.json"
companion/run boot --profile "$profile" --output "$attempt" --seconds 7200 \
  --overlay-base-report "$base" --disk-boot --launchd-unsecure-cache \
  --guest-errors --capture-interval 30 --probe-journey --control-mailbox \
  --touch-trace-startup --touch-trace-seconds 900 \
  --guest-hid-serial --probe-keep-running
```

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
