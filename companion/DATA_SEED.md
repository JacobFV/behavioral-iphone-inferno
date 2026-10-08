# Seed original Data through one recovery stage

`stage-seed-data.py` accepts a hash-pinned successful `initial-volumes.json` and
replays its actual role-only serial inventory, pre-finish checkpoint, sole normal
finish, stopped report, seven frozen identities and full backing hashes. The
inventory must contain exactly the original System, Preboot, xART and Hardware;
Data or Update is rejected. The original raw ancestor is 8 GiB. The initial
chain has two layers, this seed adds a third, and a separate read-only tree
verification can add the fourth. Further work requires a separately verified
flattening step rather than exceeding the existing chain limit.

Invoke `python3 companion/stage-seed-data.py --help` for the required path/hash
pairs: initial-stage, verified profile, plain recovery extraction record, actual
preparation-helper build record, probe, hfsplus, emulator and build manifest.
Also provide the pinned overlay tools directory and a new external output.
All inputs are read-only. A private umask applies to fresh outputs and children.
The exact ramdisk job is extracted and checked before starting the one VM:
`inferno-prepare-root --disposable-root-copy --existing-volumes --seed-data`.
There is no keybag, gigalocker, cache, helper installation or application operation.

The coordinator checks actual original newfs/mount status, six-volume discovery,
before/after APFS available space, bounded original copy-path records and ordered
Hardware/Data/System clean unmounts before accepting DATA_COMPLETE/PREP_COMPLETE.
Available space must remain positive; successful copy calls also remain mandatory.
It saves and pins that serial prefix before issuing its only finish-observation.
After normal QMP shutdown and emulator exit, it checks sources, prefix and
metadata again, freezes **only the seven new files**, preserves them through the
ordinary stopped verifier and validates the complete ancestor chain. Failure
retains INCOMPLETE/failure evidence and never publishes a successful result.

The output `seeded-data.json` has status `seeded-not-byteverified`,
`tree_bytes_verified: false` in its raw content result, and
`ipa_runtime_ready: false`. Copy-path success does not prove byte equality.
The next phase must independently mount System and Data read-only and compare
bytes, metadata, symlinks and extra entries using `--verify-data` **without**
`--seed-data`; the existing helper verifies before copying if both are requested.
No installed-iOS boot or app success is asserted by this recovery tool.
