# Separate Data verification

`stage-verify-data.py` consumes a successful `seeded-data.json` and its hash. It uses the same explicit profile, plain recovery extraction, helper-build, marker, HFS tool, emulator/build and overlay-tool pins as the preceding stages. `--seed-stage` replaces the preceding coordinator’s input-result argument. Output must be a new external directory.

The coordinator prepares exactly `--existing-volumes --verify-data`, reads back the helper and launchd job, then runs one recovery VM. It discovers volumes and mounts System and Data read-only. The existing helper compares original `/private/var` against Data, including regular bytes, size, mode, owner/group, symlink targets, missing and extra entries. It does not compare ACLs, extended attributes, timestamps or compression encoding. Combining seed and verify flags is forbidden: the helper’s verification branch precedes its seed branch.

A unique zero-mismatch tree result must precede successful Data/System unmounts and COMPLETE. Only then does the coordinator issue one normal finish, verify actual shutdown, freeze its seven new files, preserve their hashes and verify the retained backing chain. Failures remain incomplete and are never automatically retried. `data-verified.json` remains `ipa_runtime_ready:false`; it is not an installed boot or an IPA launch result.

The required input has three layers including its raw base. Verification produces four. **Flatten the successfully stopped verification tuple before keybag initialization** using an independently reviewed, exact logical comparison and source-preservation procedure. Keep all original ancestors and the six paired auxiliary states. This command does not flatten or initialize keys.

The first fresh-stage run passed the original guest comparison: 16,665 entries, 13,025 files, one link and 269,210,433 bytes with zero mismatches, followed by normal shutdown and preservation. Actual records are in `evidence/data-verify-stage-1-actual/`; the independent audit is in `evidence/data-verify-stage1-independent/`.
