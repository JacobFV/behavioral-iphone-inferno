# Stage coordinator host review

Source candidate `2824c53379`, `b4b2117174`, `85a09b0185`, with shared
validator fixes `ade91fa008`/`d9133312d9` (locally `01587223aa`/`62ba73b47e`).
Independent review: `9b11567100`.

The actual retained normal session2 report passed the coordinator's normal
report/raw-QMP shutdown gate. Both actual earlier failed staging reports rejected.
The command is constructed from pinned fields, not executed from session argv.
`report-gates.json` retains exact input/source hashes and the derived command.
No coordinator VM, chmod or preservation invocation has occurred.

A full read-only session2 replay first exposed a new shared-API shape mismatch:
`validate_runtime` returns `(paths, verified)`; the new context field initially
held the tuple. The return assignment was corrected before any coordinator run.
The next replay validated session/runtime and the normal report, then the final
stopped verifier rejected at its readable-descriptor guard:

```
ValueError: Stopped namespace has an open descriptor: /proc/3589689/fd/13 -> /home/brandonin/.local/share/inferno/app-import/prepare-session-demo-2/recovery-run/disks/root.qcow2
```

Run77 was legitimately using that retained stage as a backing disk. This is an
actual active-backing rejection, not a failed staging operation. A new positive
stopped replay awaits its release; the earlier successful stage2 verification
remains unchanged. No concurrent follow-up disk hashes are being run.

After run77 stopped and released its descriptors, the same read-only replay
completed in56.025s: actual session/runtime revalidation, normal report/raw-QMP
checks and full stopped eligibility all passed. Both earlier failed reports still
rejected. `stopped-positive.json` preserves the returned verified evidence and
source/input hashes; `replay.py` records the exact read-only invocation logic.
No disk modes, reports, retention manifests or guest state were changed.
