# Guarded Finish Setup → counter sequence

This is an explicitly invoked experiment, not an automatic boot path. Root must first review the actual current Finish Setting Up iPhone overlay over the owned counter at zero. No worker has executed this sequence on a guest.

The reference manifest pins full original VNC images from root-reviewed runs69/70. RGB comparison uses all1,081,600 pixels of `(0,100,832,1400)`, with zero tolerance. Only the clock/status strip and bottom owned diagnostic region are excluded. Dimensions remain832×1792. QMP828×1792 captures are separately retained and never resized or used as interchangeable reference images. Root must review a new reference before any future unknown state can be accepted; animation/alpha-blended states classify unknown and never authorize input. During only the bounded no-input settling poll, they may be observed until an exact zero match arrives; initial/pre-NotNow/final-pre-counter gates remain strict. Unknown frames/counts are retained, and timeout aborts without counter input.

Read-only replay:

```sh
python3 companion/guarded-setup-counter.py \
  --references companion/evidence/guarded-setup-counter/references.json \
  --references-sha256 209aa6cebf165fbdf4297fd91a0c82635d1c3af276bf575a310506a623385e6b \
  replay /absolute/path/actual-frame.png
```

Explicit root-only runtime invocation, after source/reference review:

```sh
python3 companion/guarded-setup-counter.py \
  --references companion/evidence/guarded-setup-counter/references.json \
  --references-sha256 209aa6cebf165fbdf4297fd91a0c82635d1c3af276bf575a310506a623385e6b \
  execute-reviewed --report /absolute/path/live-report \
  --output /absolute/path/new-evidence-directory \
  --boot-uuid ACTUAL-CURRENT-BOOT-UUID --delay-seconds 10
```

The only VNC client is shared AF_UNIX/no-input. All QMP goes through the existing runner mailbox. Preconditions require one boot/owned relay identity, validated appeared0, no prior tap or relay rejection, unused operator capture-before, exact reviewed overlay and all nine ADP trace events disabled. It starts a dedicated60s trace window, rechecks overlay/identity and sends Not Now once through owned-control. After exact zero matching and its actual guest ACK, the existing probe-capture-before source gate runs. Final zero-frame, same-identity and deadline checks precede one counter tap. No retry, Home, OPEN, CPU logging, strict-after or finish is invoked.

Timing uses the receiver's host monotonic write-begin timestamp, retained in the actual transport response; the wall/monotonic bracket is also retained and crosschecked within50ms. This is a host send-start deadline, never a guest-delivery deadline. The optional HID send_deadline_monotonic is validated finite/unexpired/within15s at client and receiver and rechecked after journal I/O immediately before serial writing. An expired request is rejected without a write; a blocking send can cross the deadline and its end/partial uncertainty is explicitly recorded. Only8–12s targets are accepted, with a0.5s late cutoff before submission. A queued request cannot be withdrawn, but the receiver independently refuses a send whose deadline has passed. A write already begun is not retractable: uncertain/partial input ends the sequence and is never retried. Owned CLI subprocesses run in a separate process group; timeout cleanup terminates that owned group including the nested mailbox CLI, never the VM. Actual send interval is recorded and marked incomplete if outside0.5s. Guest ACK indicates an attempted report, not visual delivery.

All full frames and raw mailbox/owned-control artifacts are retained. The fixed30s observation does not assert success from a marker or screenshot filename. Root reviews pixels. Trace remaining time is conservatively calculated from before-start submission; at least35s is required before counter submission. Existing runner owns deadline disable even if this process fails. This script does not stop/restart the runner or extend the trace. A capture can block up to the existing client's15s receive limit; deadlines are rechecked and late counter input is suppressed. Observation coverage overruns are explicitly incomplete.

Do not run other input/control sequences concurrently. Identity is evidence from the original guest relay, not peer-PID authentication or a new host process-liveness query. Exact image checks, source gating and retained provenance constrain this experiment; they do not prove hardware-rendering health.

Validation: frame-replay.json retains actual69/70 overlay/zero acceptance and beta/counter/boot/Clock rejection, plus actual828-wide QMP rejection. Synthetic alpha-blend and clock-only pixel edits are clearly labeled. deadline-fixture.json uses a real private Unix socket and existing transport: timely/default sends, expired queued validation, and an injected50ms journal delay causing rejection before write with no peer bytes. This is neither a QEMU run nor a guest/UI journey.

Run71 preflight fix: ADP trace-event-get-state is not exposed by the existing mailbox allowlist. The helper therefore verifies the last completed nine-event display trace lifecycle has all_disabled=true/pending=[], and binds every final disable response to the exact latest QMP send/ACK IDs from retained journals. Missing/partial/uncertain or pending state fails closed. No pending mailbox requests are permitted. This is conservative retained-state evidence under the sole-runner/no-concurrent-operator requirement; the subsequent existing trace-start also rejects pending state. No new QMP connection or receiver change is needed.
