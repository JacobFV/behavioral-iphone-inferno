# First original-volume phase (not an installed runtime)

`stage-initial-volumes.py` runs one explicit recovery VM. It is a new first-phase
coordinator, not an IPA installer. Only existing helper behavior is selected:
add Preboot/xART/Hardware, discover original System, copy original firmware into
Preboot, sync and unmount. No Data/Update, SEP/keybag, cache patch, app, growth,
migration or Setup operation is selected. No automatic retry occurs.

Inputs are absolute, hash-pinned records/files. The root must be a NEW retained
read-only copy of the known original System-only8GiB wrapper; arbitrary previous
roots are rejected even if a JSON record calls them fresh. Historical source
files are never chmodded. Required copy schema `inferno.original-system-copy.v1`
records the original wrapper path/hash, source path/hash/identity and new copy
path/hash/identity. Both content hashes must equal the known original wrapper.
Only a separately authorized new-copy operation should produce that record;
never rewrite the historical wrapper JSON. Root2Data/setup state is not reusable
as an original source. The actual new copy is full-hash verified before launch.

```sh
python3 companion/stage-initial-volumes.py \
  --profile ORIGINAL_PROFILE --profile-sha256 PROFILE_SHA \
  --raw-recovery-record EXTRACTION_JSON --raw-recovery-record-sha256 EXTRACTION_SHA \
  --root-copy-record COPY_JSON --root-copy-record-sha256 COPY_SHA \
  --helper-build BUILD_JSON --helper-build-sha256 HELPER_BUILD_SHA \
  --probe PROBE --probe-sha256 PROBE_SHA \
  --hfsplus TOOL --hfsplus-sha256 TOOL_SHA \
  --binary EMULATOR --binary-sha256 EMULATOR_SHA \
  --build-manifest MANIFEST --build-manifest-sha256 MANIFEST_SHA \
  --overlay-tools-root TOOLS --output NEW_EXTERNAL
```

The extractor/profile binding, helper's four source pins/binary, emulator build
and exact original root hashes must pass before execution. Existing prepare.py
produces the cloned recovery image. Coordinator reads back helper/probe and the
exact role-only launchd job before starting a1200s bounded recovery attempt.
Its process/source/freezing/preservation mechanisms reuse stage-import support;
only its owned child process group can be stopped during cleanup.

Raw verification requires exactly three successful original newfs commands,
four discovered expected volumes, exact mount ordering, the copy/unmount success
code path and original ordered final unmount output, then PREP_COMPLETE. These
are not a separate firmware-tree byte comparison or authenticated guest nonce.
The content checkpoint precedes exactly one finish-observation. Normal report,
source/profile/runtime bindings, QMP shutdown, process disappearance and standard
seven-file/backing preservation follow. Only NEW namespace files are frozen.
Existing ancestor modes and historical records remain unchanged.

`initial-volumes.json` is consumable only with no INCOMPLETE/failure marker. It
states `initial-volumes-prepared`, `ipa_runtime_ready:false`; it is not accepted
as an imported-app verification result. All failed/uncertain attempts are
forensic only. Source and raw marker checks are point-in-time evidence, not an
exclusive host lock. No runtime execution has been established merely by building
or host-reviewing this coordinator; an actual allocated recovery run is required.
