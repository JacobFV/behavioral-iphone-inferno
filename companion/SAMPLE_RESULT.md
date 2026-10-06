# Read-only sample reconstruction

After an explicit sample attempt, retain the original serial log and its owned-control `request.json`, then run:

```sh
companion/run sample-result --serial REPORT/serial.log \
  --request ACTION/request.json --output /outside-git/new-sample-result
```

The output directory must be new. Keep decoded `output.bin` outside Git (or in an ignored report directory); it contains original tool stdout/stderr. The parser sends no commands. It preserves the serial snapshot hash, exact physical LF record offsets/hashes, request identity and completion flags in `result.json`.

Exit zero establishes complete bounded transport only: matching REQUEST/BEGIN/END identities, contiguous DATA offsets and decoded lengths, matching byte/chunk totals, successful tool exit/reap, EOF, post-target match and no failure/truncation flags. Exit one retains incomplete evidence and any validated contiguous DATA prefix. Invalid CLI inputs exit two. Rerun against a later serial snapshot using a new output directory if an explicitly requested sample is still running; never resubmit the guest request automatically.

`output_usefulness` remains `not_assessed`, including for empty output. Inspect the original tool's output before claiming useful stacks. No parser result proves native performance, atomic PID identity, or the cause of a display stall.
