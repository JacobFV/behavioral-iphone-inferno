# Read-only sample reconstruction

The original-tool command is available only in a guest that advertises the matching
`INFERNO_SAMPLE_READY` boot UUID. Helper55 executed both targets successfully in run49: twenty stackshots each,
complete transport and original-tool exit0. These are healthy reference samples;
they do not identify the intermittent display-stall cause. Earlier frozen50 guests
do not support the command.

After reviewing the current guest state, submit one explicitly selected target:

```sh
companion/run owned-control --report REPORT --output NEW_ACTION_DIR \
  sample --boot-uuid CURRENT_BOOT_UUID --target BACKBOARDD
```

`SPRINGBOARD` is the other fixed target. The lifetime limit is two attempts total;
there is no arbitrary PID, command, or automatic retry. Wait for the matching
END or FAILED record before another action. The helper blocks its HID/OPEN
commands while its tool child remains active. Sampling uses the unchanged original
`/usr/sbin/spindump`; its output may report denied or unsupported operations.
Do not interpret host transmission as successful sampling. The watchdog uses
cooperative guest time, and sampling perturbs scheduling. See
[native command constraints](native-probe/SAMPLE_CONTROL.md).

After an explicit sample attempt, retain the original serial log and its owned-control `request.json`, then run:

```sh
companion/run sample-result --serial REPORT/serial.log \
  --request ACTION/request.json --output /outside-git/new-sample-result
```

The output directory must be new, its parent must exist, and the CLI requires Git to confirm that the destination is outside a worktree or actually ignored. Keep decoded `output.bin` outside Git (or in an ignored report directory); it contains original tool stdout/stderr. Reviewed plaintext diagnostic reports may
be retained as execution evidence; Apple implementation binaries stay outside Git.
The parser sends no commands. It preserves the serial snapshot hash, exact physical LF record offsets/hashes, request identity and completion flags in `result.json`.

Exit zero establishes complete bounded transport only: matching REQUEST/BEGIN/END identities, contiguous DATA offsets and decoded lengths, matching byte/chunk totals, successful tool exit/reap, EOF, post-target match and no failure/truncation flags. Exit one retains incomplete evidence and the validated contiguous DATA prefix after the unique matching REQUEST/BEGIN. Missing END, CHILD_STOP, malformed or failed records preserve earlier valid bytes; decoding stops at the first bad chunk and never resumes later. Invalid CLI inputs exit two. Rerun against a later serial snapshot using a new output directory if an explicitly requested sample is still running; never resubmit the guest request automatically.

`output_usefulness` remains `not_assessed`, including for empty output. Inspect the original tool's output before claiming useful stacks. No parser result proves native performance, atomic PID identity, or the cause of a display stall.
