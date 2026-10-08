# Durable installed wrapper: failed interaction, correctly retained failure

This is NOT a successful installed-app journey. Root observed Count0 after one
acknowledged counter tap and repeated no-input observation. Generic demo telemetry
does not prove the app received the callback; the cause is not established here.

The independent audit checks the actual persistent source/session/stage bindings,
fixed boot argv and retained prelaunch validation snapshots. The selected new
session binds revision3f8b2d5623, not session2's older runner. Operator SIGINT2 to
runner3991121 is followed by raw QMP quit/host shutdown and emulator exit0, but
attempt_completed=false/Signal2. There is no finish-observation request. Normal
wrapper verification rejects this report. Wrapper runner_exit_code1 retains
failure.json and INCOMPLETE.json, app_execution_asserted=false, with NO
completed-run.json. Wrapper3989205/runner3991121/emulator3991816 are absent.

`audit.py` and `result.json` retain hashes/byte offsets, the sole named counter
request703788b2ec02444dbd48b31236cafdb6 and raw down/up0/ACK0 delivery=unproven,
operator stop and raw cleanup. No input, VM action, source mutation, disk freezing
or repeated namespace hashes occurred in this audit. Bootworker's separate
failed-attempt retention is forensic and cannot promote this run to a base.
Visual evidence remains the root's separate review; this script classifies no
pixels. The durable host workflow preserved its failure boundary as designed.
