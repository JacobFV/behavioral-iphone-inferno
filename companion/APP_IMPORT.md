# Owned IPA import (first subset)

`app-import.py` imports an owned, unencrypted iOS device app into a new directory
outside every Git worktree. This is host preflight, not installation, signature
validation, an app launch, or evidence of general IPA compatibility.

```sh
python3 companion/app-import.py --ipa /external/Owned.ipa --output /external/new-import
```

The first subset requires exactly `Payload/Name.app`, one thin ARM64_ALL
little-endian executable, `APPL` metadata, a non-Apple bundle identifier, explicit
iPhone device family, matching plist/Mach-O minimum OS at most 14.0, and only
absolute system-library dependencies. Dependency availability remains unverified.
Fat executables, arm64e, simulator/Catalyst, nested frameworks/extensions/apps,
additional executable files, encrypted Mach-O/ZIP, symlinks, special files,
case-colliding paths, and auxiliary archive payloads are rejected. Limits are
4,096 tree entries, 128 MiB expanded/archive, 64 MiB per file, 511-byte ASCII
paths and depth 16; compression ratios are bounded. These are intentional first
release constraints, not a claim that other apps cannot run on the backend.

File bytes, including existing signatures, are preserved. No signing or
provisioning occurs. Executable mode is normalized to 0755, resource files to
0644 and directories to 0755. Extraction follows full archive preflight; an I/O
failure can leave an incomplete new directory, which must not be consumed.

The result is `manifest.json` plus `bundle/Name.app`. Keep the original IPA:
`validate_manifest(path)` (also `validate_import_manifest`) reparses that retained
IPA and revalidates the entire extracted tree, metadata and compatibility. It
returns manifest fields plus `resolved_bundle_path` and `manifest_path`. Callers
must pin the manifest hash and use this shared validator before staging/building
launch configuration. This does not eliminate concurrent source-change races;
staging must read back copied bytes against the pinned records.

Schema `inferno.owned-ipa-import.v1` records input identity, bundle identity,
sorted directory paths, sorted file records (`path`, `bytes`, `sha256`, integer
`mode`), Mach-O findings, bounds and importer source hash. `tree_sha256` hashes
ASCII JSON of exactly `{"directories": [...], "files": [...]}` with sorted keys,
compact separators and `ensure_ascii=True`, without a trailing newline. The
validator rederives the schema from the original archive; it does not trust a
handwritten manifest to waive compatibility checks. Historical importer hashes
are retained as provenance, while current validation rules apply.

The retained host check packages the existing owned fixture, imports it,
compares original file bytes, and rejects malformed archive/platform/encryption
cases. Its results are under `evidence/owned-ipa-import-host/`; all IPA/app bytes
remain external. Actual staging, launch and reviewed output are separate gates.
Xcode projects still require a real macOS/Xcode build producing a device app/IPA;
this importer is not a Linux Xcode implementation.

## Bound launch helpers to the imported app

`companion/run build-import-launcher` accepts `--manifest`, its required
`--manifest-sha256`, an installed `--linker` (ld64.lld), and a fresh external
`--output` directory. It revalidates the import and builds only our launcher and
credential-dropping wrapper. The target path and identifier are compiled into
these helpers; the imported executable and its signature are never modified.
The generated owned launchd job uses the existing cache-merge workflow. A loose
plist alone does not configure the installed guest's cached jobs.

The compiled launcher requests original LaunchServices registration and launch
for that exact target. It classifies the actual `/Applications` target as System
without adding signer or provisioning claims. The probe-specific `--open-only`
route is rejected for manifest launchers: the current HID OPEN protocol still
validates the fixture's identity. Generic relaunch and process verification need
a separately integrated path. A successful helper build or service callback is
not app execution evidence.

The first imported-fixture guest test deliberately reuses the existing launcher
and cached job because its path, identifier and executable bytes are unchanged.
Runs75 and77 exercised the manifest-configured helper with the distinct ImportedDemo
app: original process listing, reviewed bundled resource text and counter0→1.

An uninstrumented app uses a normal disk boot with the control mailbox and HID
serial input, without `--probe-journey`. Preserve original process listings and
reviewed VNC/periodic QMP frames as execution evidence. After observation,
`companion/run control --report ATTEMPT finish-observation` requests normal
runner cleanup and QMP shutdown. This command asserts no app or journey success
and is rejected when a probe journey is active; its existing completion gate
still applies. Runs75 and77 completed this uninstrumented guest journey and normal shutdown; retained
visual evidence is in `evidence/ipa-demo-75-visual/` and `evidence/ipa-demo-77-visual/`. This single app does not
establish general compatibility or resolve the intermittent display freeze.

## Prepare a complete host session

`companion/run prepare-import --ipa /external/Owned.ipa --runtime /external/runtime.json
--runtime-sha256 SHA256 --output /external/NEW` performs import, bound helper
build, one owned cache-job replacement, and recovery ramdisk preparation. It
never boots, modifies base disks, freezes files or declares an app successful.
The command retains each subprocess log and checks source and input hashes again
before publishing a successful session.

Runtime schema `inferno.local-ipa-runtime.v1` requires exact `inputs` pins
(`path`, `sha256`) for profile, raw_ramdisk, probe, disk_helper, helper_build,
hfsplus, clang, linker, cache, base_report, emulator and emulator_build; also
`overlay_tools_root`, `cache_binding`, and `tool_invocations` (exact clang/linker
invocation paths whose resolved binaries must match the corresponding pins).
This preserves the `ld64.lld` driver name while hashing its real binary. All paths must be absolute regular
unaliases (resolve tool symlinks when making the descriptor). The helper build
must bind the current preparation sources and binary. Existing profile and
recorded-overlay validators check original components and all base dependencies.
The base must have depth available for both recovery and installed child layers.

The cache binding is explicit selected configuration, **not independently proved
current guest cache identity**. It requires basis
`reviewed-retained-lineage-not-fresh-guest-export`, exact `base_report_sha256` and
`cache_sha256`, pinned original `install_profile`, `install_report`,
`install_serial`, `cache_readback`, `raw_ramdisk_preparation`, and a nonempty list
of pinned `lineage_evidence`. The fixed checks bind the original profile/cache
readback and actual raw successful cache-install marker; every retained lineage
reference must exist and hash-match. A reviewer still assesses the intervening
lineage. No arbitrary JSON predicate can waive these checks. Actual new recovery
readback is required later. Supply local firmware/cache/base assets yourself;
the command distributes none.

Successful output contains `session.json` with status
`host-prepared-not-staged`, pinned artifacts, exact subprocess logs, expected
recovery markers and a proposed recovery argv. `INCOMPLETE.json` or failure output
must not be consumed. Every prepared HFS readback is checked; base dependencies
are reverified after host preparation. No existing app collision exception is
provided by this generic command. Failed recovery clones are never eligible.


## Verify actual recovery before an app boot

The prepared session is not an installed image. Recovery runs with the control
mailbox and no probe journey. After original guest readbacks and PREP_COMPLETE,
record a content checkpoint before requesting normal shutdown:

```sh
companion/run verify-import-stage --session /external/session/session.json \
  --session-sha256 SHA --serial /external/session/recovery-run/serial.log \
  --output /external/session/content-check.json
companion/run control --report /external/session/recovery-run finish-observation
```

The content check is explicitly ineligible for boot. Once the runner and emulator
have exited normally, retain the seven new namespaces and their unchanged
ancestors. Only newly created stage files may be frozen; never change an
ancestor's permissions. Standard `preserve-stopped` records the final identities.
Then run the stopped verifier:

```sh
companion/run verify-import-stage --session /external/session/session.json \
  --session-sha256 SHA --report /external/session/recovery-run/report.json \
  --retention /external/session/recovery-run/stopped-disk-hashes.json \
  --content-check /external/session/content-check.json \
  --output /external/session/stopped-stage-check.json
```

The verifier checks original records, the pre-finish checkpoint, actual normal
finish and QMP shutdown, source/profile bindings, all seven disks and remaining
overlay depth. A historical SIGTERM preparation does not pass this normal-finish
contract. Session2 completed this route with original readbacks, normal exit0 and
eligible stage verification; see `evidence/prepare-session-demo-2-actual/`.
Eligibility permits the next installed boot; it does not prove app execution.

## Run one recovery staging attempt

`stage-import.py --session /external/session/session.json --session-sha256 SHA256
--output /external/NEW-stage` explicitly launches **one recovery VM**. It constructs
fixed boot arguments from validated session fields rather than executing the
session's command string. It rejects an already-running emulator visible in
`/proc`, uses a private child session and a 1,200-second preparation deadline,
and never retries an uncertain finish request.

Actual raw preparation records must pass the imported-stage verifier before a
content checkpoint is written and the single `finish-observation` request is
sent. Normal report/QMP shutdown and process disappearance precede freezing.
Only the seven newly allocated files inside this fresh report are frozen, via
verified descriptors, with identity/hash and readable-FD checks. Parent/backing
files are never chmodded. Default stopped preservation and the stopped stage
verifier must then pass before `verified-stage.json` is published. A consumable
result additionally requires both `INCOMPLETE.json` and `failure.json` to be
absent; the eligibility JSON alone is insufficient.

Any failure retains `INCOMPLETE.json` and `failure.json`, logs and possible partial
freeze records. Do not consume that directory even if an intermediate report
looks successful. Cleanup signals only the coordinator's owned runner/private
process session. Forced cleanup is forensic, never eligible. The readable `/proc`
checks are point-in-time and do not provide an exclusive host-wide lock.
Successful staging is still not app execution: installed boot, launch and visual
review remain separate explicit steps. No app gestures, Home, OPEN or sampling
are sent by this command.

The corrected coordinator completed its first actual automatic recovery in
`evidence/stage-coordinator-first-success/`: raw content check before exactly one
normal finish, new-file freezing, ordinary retention and final eligibility. The
earlier source-inventory failure is retained separately. Run79 then completed the separate installed-app journey from this output: original
process presence, reviewed bundled text and counter0→1, normal shutdown. Its
visual evidence is in `evidence/ipa-demo-79-visual/`. These are owned-app results,
not general IPA compatibility or a fix for the intermittent display freeze.

## Boot a verified imported stage

```sh
./companion/run boot-import \
  --stage /external/STAGE/verified-stage.json --stage-sha256 SHA256 \
  --session /external/PREPARED/session.json \
  --output /external/NEW-INSTALLED-ATTEMPT --seconds 1200
```

This explicitly starts one installed guest after rerunning the full session and
raw stopped-stage checks. The original installed profile, emulator/build and
newly verified stage are derived from pinned fields. The sibling `boot.py` and
`qmp_control.py` must exactly match the session source pins; use its reviewed
stable host tree. A newer host runner is not silently accepted because a separate
manual attempt worked. No profile/base/argv override is offered.

Output must be new and outside Git. The guest uses a fresh child overlay and
paired auxiliary copies; no source disk is changed or frozen. Duration is1..3600s
(default1200). The existing headless display and sole control mailbox are enabled
at `NEW-INSTALLED-ATTEMPT/boot`. Operators may review frames and explicitly send
ordinary controls or `finish-observation`; the wrapper sends no gestures, OPEN,
Home, samples or CPU diagnostic. It does not enable fixture-specific telemetry.
The installed owned launchd job may attempt the app's normal launch.

`completed-run.json` means normal runner/QMP shutdown only, with
`app_execution_asserted:false`. Require no INCOMPLETE/failure marker. App launch,
visible output and disk retention are separate checks. Failed or uncertain
attempts retain logs and failure markers, stop only their owned child session,
and never retry or become an eligible next base automatically.

The first actual wrapper run81 passed full stage revalidation and normal wrapper
completion. Separate root-reviewed frames showed the imported bundled text and
counter0→1. Evidence is retained in `evidence/boot-import-81-visual/` and the
wrapper execution record. This uses the pinned baseline host tree and does not
establish compatibility with other runner revisions or arbitrary IPAs.
