# Imported-stage verifier candidate

`import_stage.verify_content(raw_bytes, validated_manifest, artifact_sizes, identical_fixture=False)` is the pure pre-finish API. It returns exact raw byte references or raises. It does not authenticate session/boot or authorize disks. Directory metadata ordering follows the staging binary plan's depth/path ordering.

`verify-import-stage.py --session SESSION --session-sha256 SHA --serial REPORT/serial.log --output NEW_CHECK.json` additionally validates the prepared session and captures a timestamped exact serial prefix checkpoint. Run before sending the existing `finish-observation` command; this verifier never sends it.

After normal stop and ordinary `preserve-stopped --output REPORT/stopped-disk-hashes.json`, use the same session options plus `--report REPORT/report.json --retention REPORT/stopped-disk-hashes.json --content-check NEW_CHECK.json --output NEW_ELIGIBILITY.json`. All outputs must be new. No preservation, source edits, disk writes or VM actions occur.

Actual retained failed fixture1/2 and demo1 raw logs reject. Demo2 raw content passes; its Signal15 report does **not** satisfy the new normal-stop contract. These are host replays, not a new recovery run. Final session validation was exercised on actual host-produced prepare-session-demo-2. Actual successful end-to-end normal recovery remains pending.

Unknown relevant owned output, malformed/duplicate/out-of-order milestones and extra install operations fail closed. Current helper records have no nonce/boot UUID: fresh single-run provenance and exact unique markers reject observed restarts but do not cryptographically authenticate pasted logs. Retention checks remain point-in-time, with `/proc` permission gaps explicitly reported and no exclusive locking claim.
