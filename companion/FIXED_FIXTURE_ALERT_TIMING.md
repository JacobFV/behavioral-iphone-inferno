# Fixed fixture alert timing

This opt-in driver is restricted to the reviewed imported fixture base and the
three reviewed run91 states. It sends beta Close, Setup Not Now and one counter
tap, targeting 43, 18 and 13 seconds after the **previous actual owned-control
submission `started_time`**, respectively. It does not equate these host times
with guest delivery or presentation.

Root first performs exactly two normal unlock swipes and retains the second
`owned-control` submission. Invoke promptly, before its first 39 seconds expire:

```sh
python3 companion/fixed-fixture-alert-timing.py \
  --report /absolute/current/report-directory \
  --boot-uuid CURRENT-GUEST-BOOT-UUID \
  --second-unlock /absolute/second-unlock/submission.json \
  --output /absolute/new/external/timing-evidence
```

The driver binds that submission to the current report, source pins, serial wire,
control response and request-specific ACK0. It requires the same frozen fixture
base/runtime as run91 and one current validated appeared/count0 app incarnation.
Root must remain the sole operator and send no competing commands or inputs.

Each step takes a fresh observation using the existing headless VNC command.
Exact RGB equality uses the fixed crop `(0,250,828,1450)` from root-reviewed
run91 images: VNC is832x1792 and QMP is828x1792. Neither is resized. The crop
includes the counter, button and alert, excluding only the changing clock/footer.
A mismatch, missing ACK, process/source drift or missed deadline aborts without
retry. Before the counter tap, the driver requests the unused strict before
capture and checks its actual QMP crop against the same reviewed counter0.

Submission must begin between the target and target+0.5 seconds. The existing
receiver's monotonic send cutoff also prevents a late serial write; timeout or
partial/uncertain transmission never causes a replay. CPU-window and ADP trace
overrides must be off. Existing startup multitouch tracing and `guest_errors`
remain permitted and unchanged; the driver does not alter diagnostics.

After the single counter tap it observes for25 seconds, records the ACK and
returns for root's visual review. It does not capture strict-after, stop the VM,
open Home, relaunch, sample stacks or issue any second counter tap. A completed
host sequence alone does not prove that pixels changed. All command logs,
submission timestamps, PNGs and failures remain in the new external output.
