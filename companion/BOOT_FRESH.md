# Installed boot of a fresh owned-runtime stage

`boot-fresh.py` consumes a `fresh-runtime.json` (`inferno.fresh-runtime-stage.v1`,
status `owned-runtime-staged-not-booted`) written by `stage-fresh-runtime.py` and
launches one explicit `boot.py --disk-boot` attempt on its three-layer overlay.
It does not claim migration, unlock, app launch or pixels; only normal runner
completion is checked.

    python3 companion/boot-fresh.py --stage <fresh>/fresh-runtime.json \
        --stage-sha256 <sha256> --output <new external dir> [--dry-run]

Before launch it fails closed unless: the result hash, schema, status, depth 3
and report/retention layout match; every recorded source/input/stopped-evidence
pin re-hashes under `runtime_rebuild.historical()` (boot.py and qmp_control.py
must also match the staged run; other host-source drift is recorded in
`launch.json`); the runtime substitution record and actual rebuilt binary and
manifest hashes match the stage and `RB.current()`; the stopped recovery report
completed normally; `disk_overlay.load_stopped_overlay` returns exactly three
layers; no emulator is running; and at least 4GiB is free. `--dry-run` stops
after these checks and prints the argv.

The fixed argv uses `--overlay-base-report <fresh>/recovery-run/report.json
--disk-boot --launchd-unsecure-cache --control-mailbox --guest-hid-serial
--guest-errors --capture-interval 10`, the verified profile, the rebuilt binary
and manifest from the stage report, and never `-initrd`. After the run the
overlay base report/hashes, normal completion, absence of `-initrd`, profile and
runtime hashes and QMP shutdown are rechecked before `completed-run.json` is
written.
