# Next initialization boundary after reproduced host inputs

The reproduced helper, raw recovery payload and unchanged prepare-import
consumer now close host artifact-production gaps. They do not create the
initialized runtime consumed by the IPA workflow. This review used source/docs
and retained metadata only; no VM, image hash, input or disk change occurred.

## What remains distinct

- `decode-udif.py`/`wrap-gpt4k.py` produce the original System-only APFS container.
  `os-image/README.md` records no Data volume. Growth uses a separate original
  APFS API operation; changing GPT geometry alone cannot increase APFS capacity.
- Original device initialization is executed in recovery on disposable roots:
  Preboot/xART/Hardware roles, original firmware copy, Data/Update and var seed,
  original gigalocker/SEP activation, effaceable query/format and original
  MKBCreateSystem. Successful phases8/12/13/17/21 are recorded in native-probe
  README. All six auxiliary namespaces must stay paired with the resulting root.
- Software-rendering cache preparation and original launchd-cache installation
  are separate operations. The current runtime descriptor binds retained
  install31/profile/readback/serial and reviewed descendant history. A newly
  initialized root cannot inherit that cache lineage merely by matching an app
  or helper hash; it needs its own actual install/readback/normal-stop evidence.
- Original migration, first unlock and Setup choices produced real guest state.
  These still require execution and reviewed ordinary UI. No current host
  producer honestly replaces those steps or supplies an app-ready base.

## Smallest useful next implementation: one initial-volume stage

Implement `stage-initial-volumes.py`, a narrowly named first-phase coordinator,
not a full installer and not a relaxation of stage-import. It should reuse the
existing helper's proven `--disk-helper-roles` operation ONLY. No Data/keybag,
cache patch, app install, Setup automation or growth is implied.

Proposed explicit contract:

```text
stage-initial-volumes.py
  --profile ORIGINAL_PROFILE --profile-sha256 HASH
  --raw-recovery-record EXTRACTION_JSON --raw-recovery-sha256 HASH
  --root-wrapper-record GPT4K_JSON --root-wrapper-sha256 HASH
  --helper-build BUILD_JSON --helper-build-sha256 HASH
  --probe PROBE --probe-sha256 HASH
  --hfsplus TOOL --hfsplus-sha256 HASH
  --binary EMULATOR --binary-sha256 HASH --build-manifest MANIFEST
  --overlay-tools-root TOOLS --output NEW_EXTERNAL
```

The records must bind actual regular files and exact original System-only source
geometry/payload hashes. Do not accept an arbitrary previous root as fresh. The
source remains retained and unchanged; require an already read-only raw source
for overlays rather than chmodding an ancestor. Build the recovery profile with
existing prepare.py, exact role-only job, and verify its HFS readbacks. Start one
explicit `--ramdisk-boot` recovery on a NEW disposable overlay; no automatic retry.

Before any next-phase claim, require raw `INFERNO_PREP_BEGIN` existing0/roles1,
exact original newfs Preboot/xART/Hardware argv/status0, discovered expected
volumes, firmware-copy completion path and clean unmounts through PREP_COMPLETE.
Tie this to the generated profile/helper/source pins, not standalone marker text.
Then one finish-observation, actual QMP host shutdown/exit0, process disappearance
and ordinary seven-namespace/backing preservation. Reuse existing process/source
and preservation mechanisms without accepting app-stage-specific assertions.
Publish `initial-volumes-prepared` with explicit `ipa_runtime_ready:false`.
Any failure retains a disposable forensic output and is never a next-phase base.

Why this phase: it is the first real filesystem mutation after the now reproducible
host inputs, has a successful historical original-API execution, and exercises
the missing fresh-source transition without combining untested initialization
orders. The current helper already has the required behavior; no guest C,
Apple implementation, signature policy or emulator change is proposed. A bounded
raw verifier for this phase is part of the coordinator, not another broad test
suite. An actual fresh-source recovery run would require a separately allocated
VM slot and review after implementation; none is authorized or attempted here.

Later work can consume this phase's actual output for Data/keybag/cache/setup,
each retaining its own gates. It must not label initial volumes as the existing
eligible initialized runtime or transplant historical cache provenance.
