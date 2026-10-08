# Initialized-runtime production map and next bounded step

Read-only review of tracked commands and retained metadata. No VM, firmware
acquisition, full image hashing or source/disk mutation occurred.

| Phase of the current lineage | Reusable mechanism | Remaining operator/history boundary |
| --- | --- | --- |
| Original n104ap18A5351d component selection | `prepare-profile.py` / `run prepare` selects the exact research erase identity from a supplied local IPSW, emits component profile/hash provenance. BOOT.md documents it. | Supplies early recovery components, not an initialized installed runtime. |
| Official System filesystem geometry | `os-image/decode-udif.py` then `wrap-gpt4k.py`; reproduced official payload/GPT hashes recorded in os-image/README. Grow uses grow-gpt4k plus original guest APFSContainerResize (GROW.md). | OS source has only System; no Data, system keybag or user setup. |
| Raw recovery filesystem for owned helper injection | `native-probe/prepare.py --raw-ramdisk` clones HFSX, installs owned helpers/jobs, performs HFS readbacks, emits profile/preparation record. New tracked helper builder reproduces helper60. | The initial `ramdisk-payload.raw` was supplied after a one-off IM4P OCTET STRING extraction. No tracked dedicated producer currently bridges prepare-profile's intact ramdisk component to this raw input. |
| APFS roles, firmware tree and Data | `prepare-root.c` plus explicit prepare.py roles/gigalocker/Data/SEP/verify flags invoke original utilities and verify copies. README records separate successful phases8,12,13,17. | The historical multistep recovery sequence is evidence, not an end-to-end fresh-runtime coordinator. Failed predecessors are not reusable bases. |
| Fresh simulated-device keybag | Original effaceable query/format, seputil load, MKBCreateSystem(NULL), shutdown/unmount through explicit helper flags; successful preparation21 retained. | Root and all six auxiliary namespaces must stay paired. No handcrafted keybag or device-key extraction. |
| Software rendering and normal launch jobs | fs-patches scripts derive bounded upstream patch plan and verify full cache/readback; launchd cache merge replaces/adds only owned jobs. Original successful cache install report31/serial/readback remains pinned in runtime descriptor. | Inputs include the retained original/patched cache and sidecar; review binds original patcher revision. No signatures changed. Later lineage is reviewed history, not inferred from file names. |
| First unlock, migration and setup | Original API helper plus simulated-SEP protocol fixes; normal Setup UI was exercised until Home. | Language/region/offline/no-passcode/setup selections and later migrations are real guest state from operator actions. There is no honest host-only substitute for repeating and reviewing this stage. |
| Current reusable base | Stopped preparation50 was logically flattened to NEW raw, qemu-img compared equal, then original50 auxiliaries and reviewed helper55 preparation created `disk-preparation-from50-sample-1`. Its raw readbacks/shutdown/retention are pinned. | This is a descendant of the initialized guest, not a clean raw OS image. Flattening changes storage representation, not installation/setup history. |
| Current IPA path | Persistent-source prepare-import→stage-import→boot-import, each with new outputs and strict pins. | This consumes the established lineage. Durable85 failed its interaction; normal/error wrapper outcomes remain distinct from pixels. |

## Recommended next implementation

Add ONE host-only narrow raw-recovery extractor, for the already supplied exact
profile/component. It should verify the profile's ramdisk SHA, parse bounded DER
IM4P structure, require the expected payload type and an unencrypted HFS+/HFSX
payload, copy its OCTET STRING unchanged into NEW external output, and record
source/profile/payload hashes and exact byte offset/length. Reject malformed,
encrypted or unsupported containers instead of adding a decryption path. Validate
against the existing retained raw payload hash without modifying that artifact.
No guest, signature, ticket or arbitrary component rewrite is involved.

This closes the earliest concrete host artifact-production gap: prepare-profile
emits the container that native-probe preparation cannot directly consume. It is
smaller and more testable than claiming a fresh-runtime coordinator over the
historical phase sequence. It will NOT produce eligible Data/keybag/setup state,
cache-install lineage or an app-ready runtime; those later phases still require
actual original-API execution and operator-reviewed setup. The initial file can
then be produced by a tracked command rather than an unrecorded conversion.
