# Grow verified Data capacity

`stage-grow-data.py` accepts pinned `--flattened-data` and the same explicit recovery/profile, marker, HFS tool, emulator/build and overlay-tool inputs as the previous phase. `--helper-build` must describe the unchanged owned growth helper produced by `native-probe/build-grow-helper.py`, not the general preparation helper. Output must be a new external directory.

This is one bounded 8GiB→32GiB operation. The coordinator first replays the three prior phase records, verifies frozen flatten provenance and paired six auxiliary states, then invokes the pinned GPT growth tool on a new private file. Both GPT CRCs and the original APFS extent are checked, source contents/identity are preserved, and only the new raw backing is frozen. The GPT tool copies through an exclusively created0600 descriptor, so an immutable0444 source is never chmodded. The source and all old reports remain retained.

Recovery contains the exact owned helper and marker read back from HFS, with only `--disposable-root-copy`. A single original `APFSContainerResize` call requests34,358,669,312 partition bytes. Normal success requires return0, increased statfs capacity, matching two original System file length/FNV fingerprints, both read-only mounts and clean unmounts, and unique completion. The helper source pins establish its fixed mount arguments and API invocation. Those two fingerprints are consistency checks, not cryptographic or whole-Data postgrowth verification.

The coordinator preserves the six auxiliary files from the verified Data tuple, issues one normal finish, and freezes/retains only its seven new outputs with a raw-backed depth2 chain. `grown-data.json` reports `grown-not-runtime-ready` and `ipa_runtime_ready:false`. It does not initialize keys, modify APFS metadata directly, install caches, complete Setup, or launch an IPA. Failures remain incomplete; no retry is automatic.

Do not run this during another VM or source/backing mutation. Host GPT expansion and recovery execution require the allocated execution slot. Initial implementation is pending independent review and an actual new growth run; historical serial replay is only parser validation.
