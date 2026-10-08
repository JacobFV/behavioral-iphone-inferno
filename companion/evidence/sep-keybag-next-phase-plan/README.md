# Next original SEP/keybag phase — read-only plan

The smallest next coordinator can use the **unchanged** existing helper with
`--existing-volumes --copy-sep --create-keybag`, on a fresh child of the reviewed
**grown-data** stage and its exact six auxiliary namespaces. Do not use an
installed/failed guest or historical keybag disk. Growth is still a prerequisite;
this note does not authorize execution or claim the new initialization succeeded.

Prepare flags are `--disk-helper-existing --sep-payload PATH --sep-sha256 HASH
--disk-helper-keybag`, with the existing pinned reproducible preparation helper,
probe, hfsplus, verified recovery profile and plain recovery extraction. Do not
add `--init-gigalocker`, seed, verify, readiness, cache, unlock, or app flags.
The exact extracted launchd job must contain only disposable-root-copy plus the
three helper flags above. Retain existing ad-hoc grants unchanged: private APFS
xART and the singleton AppleEffaceableStorageUserClient class.

## Inputs and provenance

The current base profile is the n104ap/iPhone12,1 18A5351d Research Developer
Erase Install profile, SHA256 `7939d609b99b8223863dba0b0af9d181526b420c0023cc9520563fd7e0979ed8`.
Its kernel, DeviceTree, trustcache and original recovery image remain those
already used by seed/verification. Use the reproduced plain recovery record
`raw-recovery-reproduced-1/extraction.json`; it binds the unencrypted recovery
payload and must still be validated, not silently substituted with an old ramdisk.

SEP is the untouched ZIP member `Firmware/all_flash/sep-firmware.n104.RELEASE.im4p`
from the same official IPSW. External input is
`/home/brandonin/.local/share/inferno/native-probe/sep-original.im4p`, 7,783,790 bytes,
SHA256 `76587673e56bbb89e178a015ebbe20fee29f841d07fa6f6cce0e9dad6800dfbe`.
This review read that file and streamed the ZIP member, independently matching
both SHA256 and the matching BuildIdentity's SHA384. No extraction output, key,
decryption, ticket, signature, or new container was created. “Plain recovery”
provenance does **not** imply that real SEP firmware executes: these unchanged
IM4P bytes are passed to the original loader under the simulated SEP backend.
The `.img4` destination suffix does not describe a conversion of the IM4P bytes.

`prepare.py` hashes the SEP input and performs an actual HFS ramdisk extraction
readback at `/usr/share/inferno-sep-payload`; require equality and retain those
commands/outputs. It records `sep_payload_sha256` in preparation/profile metadata.

## Required actual sequence and gates

1. Discovery must identify System, Data, Preboot, xART, Hardware and Update.
   Bind this inventory to the grown predecessor and all seven copied namespaces.
2. Mount Preboot writable at `/mnt2`, copy the supplied bytes to the existing
   96-zero firmware path `usr/standalone/firmware/sep-firmware.img4`, sync and
   cleanly unmount. Require `INFERNO_SEP_COPY_COMPLETE` and no copy failure.
3. Mount xART writable `/mnt7`, Preboot **read-only** `/mnt1`, Data writable
   `/mnt2`. Run original `seputil --gigalocker-init`, then
   `seputil --wait --load /mnt1/<96 zeros>/usr/standalone/firmware/sep-firmware.img4`.
   Require both raw utility statuses0. Retain original SEP activation messages
   as observations, not real secure firmware execution or cryptographic proof.
4. Original IOKit opens AppleEffaceableStorage, selector3 queries formatted state.
   For this fresh lineage expect status0/count1/formatted0, selector4 format0,
   then selector3 recheck0/formatted1. The helper skips formatting if already
   formatted; a fresh-stage coordinator should reject that unexpected branch
   rather than relabel it new initialization. No selector7 clear or raw writes.
5. Original `MKBKeyBagCreateSystem(NULL, "/mnt2")` creates the bag; require
   CREATE_BEGIN followed by result status0, stat0 and a nonempty regular file.
   Historical success was 223 bytes/mode100644; retain actual new values.
   Existing-bag status -4 is accepted by the general helper but **must not be
   promoted as fresh creation** by the new coordinator.
6. After SEP load, require original `seputil --gigalocker-shutdown` status0,
   sync and ordered clean Data, Preboot, xART unmounts, mounted-count0,
   KEYBAG_COMPLETE then PREP_COMPLETE. Save/check exact serial prefix before the
   coordinator's sole normal finish-observation. Require QMP normal quit,
   emulator0, all processes absent, source/backing unchanged, new-only freeze
   and ordinary seven-file retention/loader validation. No SIGTERM promotion.

## Readback limit and historical order

Current `copy_sep` has **no destination byte comparison**; the available readback
is the ramdisk input, followed by copyfile success and original loader status.
Do not report destination SEP bytes as independently verified from those markers.
Historical container-growth-2 separately extracted the complete SEP file and
matched its hash, but that proves only its own old disk. A new destination-byte
claim needs a separately reviewed destination readback (or a future narrowly
scoped helper extension); this plan makes neither change nor claim.

Historical prep12 initialized fresh xART before seed13, SEP copy14 and growth2.
Its init-only shutdown experiments had hung before SEP activation, so init-only
was deliberately unmounted without shutdown. Prep21 later loaded SEP, queried
fresh effaceable state0, formatted/rechecked1, created bag status0 and shut down
before all three unmounts. Earlier prep18/19 failures are retained, not success.
The new lineage has not initialized gigalocker or keybag; the keybag helper's
own `--gigalocker-init` handles that step. Do not replay the old experimental
loop or add a separate redundant initializer.

Preserve root, firmware, syscfg, ctrl_bits, nvram, effaceable and panic_log as one
paired state. Effaceable/nvram and xART may change through original APIs; their
new hashes are outputs, never reasons to restore blank auxiliary files. The
smallest result should be `fresh-keybag-created-not-runtime-ready`, with explicit
`sep_destination_bytes_verified:false` and `ipa_runtime_ready:false`. It does not
establish first unlock, installed-iOS boot, Setup completion, app execution,
real SEP security, or user credential recovery. No keybag contents belong in logs.
