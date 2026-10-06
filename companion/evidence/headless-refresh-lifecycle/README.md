# Bounded observer lifecycle checks

`check.py` uses a private Unix fake RFB 3.8 server and the actual observer subprocess. It verifies shared-client/no-input wire behavior, finite expiry, early SIGTERM report preservation, child reap, socket-namespace cleanup ordering, bounded duration validation and separate raw observer process sampling. This is not an emulator or iOS execution test.

The runner flag defaults to disabled. With `--headless-refresh-seconds 1..300`, a single no-input observer begins after QMP cont, without blocking the sole QMP loop. The observer context exits before the temporary socket directory, including on exceptions. SIGTERM requests a controlled partial report; three seconds later a still-live owned child is killed and reaped with a further three-second bound. Cleanup errors are retained without suppressing normal QMP quit. Forced termination may prevent a final child report and is explicitly incomplete.

`lifecycle.json` records actual connection/first-frame/close boundaries, requested-phase completion, source hashes and child identity. `resources.jsonl` retains sampled raw Linux proc stat separately from emulator resources; CPU is a sampled delta and peak RSS is sampled, not exact lifetime accounting. This active refresh workload is not passive observation, and is not claimed to fix the earlier missing-submission stalls. Frame receipt is not guest presentation.

Actual iOS integration remains for the parent-runner trial after source review.
