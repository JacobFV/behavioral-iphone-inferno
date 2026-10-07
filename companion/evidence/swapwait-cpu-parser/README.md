# Bounded SwapWait CPU dump analysis

Run against an explicitly preserved raw log, with an output path that does not exist:

```sh
python3 companion/evidence/swapwait-cpu-parser/parse.py \
  --input /absolute/path/guest-errors.log \
  --mode kernel-zero-slide --output /absolute/path/cpu-snapshots.json
```

Before interpreting kernel records, independently verify the attempt's zero kernel slide, pinned original kernel/ABI, exact emulator command and diagnostic control journal. The parser does not establish those conditions. It recognizes only the reviewed entry `fffffff0096df690` and final wrapper continuation `fffffff0096e219c`. Other observed PCs are retained without ABI interpretation.

Each record retains raw text, byte offsets, hash, all full-width registers and structural errors. Complete records require all 31 GPRs, PC, SP and the PSTATE footer in the original dump layout. Incomplete blocks and orphan register/footer fragments remain explicit. The output is not a reproduction of unrelated guest-error lines; retain the hashed original input alongside it.

Entry distributions derive W1/token, W2/flags and W3/third; return distributions derive W0/status. These are snapshot distributions, never invocation counts or paired calls. No CPU/process/thread identity or causality is inferred. Logger scheduling and `nochain` perturb execution.

`--mode owned-attempt-6` uses only the previously executed fixture's exact PCs. Validation records an offline replay of its 922 complete snapshots, plus separately labeled synthetic malformed/truncated inputs. This is not an iOS execution test. The fixture's raw mailbox reply contains the production filter descriptor; its actual command and observed PCs establish its synthetic filter.
