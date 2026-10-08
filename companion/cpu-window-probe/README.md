# Fixed SwapWait GPR window

`boot --swapwait-cpu-diagnostic --guest-errors --control-mailbox --disk-boot ...`
opts in to two fixed four-byte TB-start filters: `0xfffffff0096df690+4`
and `0xfffffff0096e219c+4`. The exact reviewed kernel, emulator binary and
build source are pinned in `qmp_control.py`. Default CPU logging stays off.
Each request also requires exactly one zero kernel virtual-slide startup line
from this attempt's emulator stderr.

After independently confirming a frozen display, the operator may request:

```
python3 companion/qmp_control.py --report /absolute/report swapwait-cpu-window --arguments '{"seconds":1}'
```

Only integer seconds 1–3 are accepted. No address or mask arguments exist.
The sole runner QMP owner enables literal `log cpu,nochain,guest_errors` and
restores `log guest_errors` at the monotonic deadline, an 8 MiB log-growth
poll cutoff (all mixed log bytes, not just CPU records), uncertain enable, or runner cleanup. Display trace windows cannot
overlap. The existing log inode/path is retained. The journal records actual
commands, responses, times and offsets. Polling/QMP delays and in-flight CPU
work can overshoot limits; this is not a hard real-time or byte-exact cap. The restore-ack offset is not the
hard last CPU sample. Per-diagnostic state/errors remain incomplete after
uncertain delivery or journal/restore errors even if the app journey independently
completed; successful restoration does not erase a prior diagnostic error.

Each dump is one coherent GPR block, with no CPU/thread identity. Do not pair
entry and return snapshots. A matching entry PC supports token/flags inspection;
the matching wrapper-continuation PC supports final w0 inspection. Neither
proves every invocation was observed. `nochain` perturbs execution globally,
even though the address filter limits output. No instruction, FPU or VPU dump
is enabled. These observations are not performance measurements or proof of
unperturbed freeze behavior.

The owned harness runs a standalone AArch64 loop under `virt`, without network,
Apple code, or firmware. Its two synthetic PCs and labeled synthetic slide
fixture exercise logging plumbing, not the production kernel-address guard.
It verifies known arguments and return registers, complete GPR blocks, absent
unfiltered PC output, actual continuing PL011 guest-error messages after mask
restoration, deadline/early-cleanup and uncertain-enable restoration. Build
products and raw logs go only to a new external output directory:

```
python3 companion/cpu-window-probe/run.py --binary /absolute/qemu-system-aarch64 --output /absolute/new-output
```

## Separate pending-branch profile

Adding `--swapwait-cpu-profile pending-branch` at boot selects only
`0xfffffff0096f1c74+4`, `0xfffffff0096f1c7c+4` and
`0xfffffff0096f1d1c+4`. It requires the existing diagnostic opt-in and pins;
there is no runtime profile change or arbitrary address argument. Baseline
remains the default. Before each pending-branch window the sole QMP owner
queries exactly the nine known ADP events and requires each disabled. This
internal fixed query does not expand the public trace-query allowlist.

`pending-branch-result.py --input LOG --output NEW_JSON` preserves complete
31-GPR blocks, malformed/truncated blocks, raw offsets and unknown PCs. At the
null branch, X11 must be zero and X10 is ignored. At the active join, X11 is
the second active-pointer read; W10 comes from the third pointer read and is
interpreted only for nonzero X11. At the queued match, X8 is the queue pointer
and W9 equals W11. W0/W1 are requested/completed tokens at the first two sites.
Modes 0/1/2 can reach these sites: mode remains unknown. No pointers are read,
no snapshots are paired, and repeated memory loads are not an atomic snapshot.
Absence of a site is not evidence its branch never occurred.

The owned harness accepts `--profile pending-branch` and substitutes three
relocated, self-authored branch sites. Parse its output with
`--owned-fixture-report /absolute/output/report.json`. The actual fixture CLI
filter is recorded in `command`/`filter`; the mailbox response reports the
production profile descriptor, not that relocated CLI filter. This verifies
logging and parser plumbing only, not actual original-kernel TB coverage.
