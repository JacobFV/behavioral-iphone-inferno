# Stage37: owned operator-only virtual touchscreen candidate

Source is stopped app-boot-16 root SHA256
11105d4cf74b837232860cd984f37920a9da3d1a68cf2e8c065b152368f890cb
and all six paired auxiliary namespaces. The original SPI firmware path remains
rejected for missing manifest digest; this candidate tests a separate normal OS
virtual HID route and does not claim that hardware path is repaired.

Staged only owned /usr/bin/inferno-hid-input, updated /usr/bin/inferno-readiness,
and the unchanged535-byte loose readiness descriptor. No launchd cache, app,
launcher, other helper, or firmware file was changed by the requested operations.
Existing readiness fresh-execs the separate input process when present. No new
launchd job or automatic gesture is added.

Input helper is68,736bytes, SHA256
3619b68952b5b6fa324f1055b74dd04250fc6c764e4241b5525cbe7e1ac0df74.
Readiness is68,672bytes, SHA256
3c360cba34c8d7616fc1ac173af4e7ebd21226f69addc9f11a2fcd6c0e8bcba1.
The owned input helper has only com.apple.developer.hid.virtual.device=true in
its own ad-hoc signature. There is no Apple identity/certificate/signature claim.
Actual original-cache audit resolves15 binds and18 dynamic symbols; source,
descriptor contract and API/authorization evidence are in native-probe/hid-input-audit.

Actual recovery serial verified HID68,736bytes and readiness+samejob69,207bytes,
with zero byte/mode/ownership mismatches. Both normal System unmounts completed,
then INSTALLED and PREP_COMPLETE. Intentional post-preparation host interruption
triggered the runner's finally block: QMP quit acknowledged, emulator exit0.
The report preserves attempt_completed=false for that early intentional stop.
All seven namespace hashes were computed only after process completion.

Final root SHA256:
860a6fe36cfbce1fcb2b3c906d42f326fe2af88e5399161980a1a3a1d6827617.
Explicit archived stable recovery emulator was used. No guest virtual-device
creation, console roundtrip, event delivery or visual response is claimed by
this staging evidence. Next full boot and explicitly triggered operator input
must establish those results separately.
