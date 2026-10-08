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

## Host and runtime prerequisites

The tested host is Ubuntu24.04 ARM64. Use Python3.11+ (the validators use
`hashlib.file_digest`) and Pillow for headless observation. Follow the local build
prerequisites in [README.md](README.md#build-and-run-the-control-plane-check);
retain the complete emulator build root and its manifest, not just the binary.
Preparation also needs pinned Clang/LLVM Mach-O linker, HFS+ tool, owned helpers
and [overlay tools](BOOT.md). The demonstrated path uses local tools without an
Apple SDK. It is not a bootstrap for arbitrary Linux distributions.

An **already initialized, retained compatible runtime lineage** is required.
An IPSW alone is insufficient: the current workflow consumes an eligible stopped
base, original cache-install evidence and matched owned helpers. Fresh runtime
provisioning/distribution is not provided by these three commands. Keep firmware,
disks, tools and generated products outside Git. No Mac is required to import an
already-built compatible IPA; building Xcode projects remains deferred.

The separate [initial-volume phase](INITIAL_VOLUMES.md) now has a bounded
coordinator for a fresh original System-only source. Its first actual recovery
validation is still pending. Even a successful result explicitly has
`ipa_runtime_ready:false`: it prepares only Preboot/xART/Hardware and the original
firmware copy. Data, keybag initialization, cache lineage, migration and reviewed
Setup remain separate prerequisites. Do not substitute this phase's output for
the eligible initialized base required by `prepare-import`.

## Retain a durable host source tree before preparation

A session pins source hashes **and their original absolute source location**.
Create its source checkout in persistent local storage before preparing it.
Keep that checkout for every later stage and boot validation. Do not relocate a
prepared session's source root, rewrite its pins, update the checkout in place,
or delete earlier frozen trees. A newer release needs a new checkout and session.

Use a reviewed full commit ID available in your local repository. These ordinary
Git commands make an independent local clone without network access, submodule
checkout or hardlinked object storage. Both destination directories must be new;
their parent must already exist. Run this block in a dedicated shell, stopping
on the first failed command.

```sh
set -eu
inferno_repository=/absolute/path/to/behavioral-iphone-inferno
inferno_revision=FULL_REVIEWED_COMMIT_ID
inferno_host=/persistent/external/host-runtimes/RELEASE
mkdir "$inferno_host"
git -c protocol.allow=never -c protocol.file.allow=always \
  -c core.hooksPath=/dev/null clone --local --no-hardlinks --no-checkout \
  --no-recurse-submodules -- "$inferno_repository" "$inferno_host/source"
git -C "$inferno_host/source" -c core.hooksPath=/dev/null \
  checkout --detach "$inferno_revision"
test "$(git -C "$inferno_host/source" rev-parse HEAD)" = "$inferno_revision"
git -C "$inferno_host/source" diff --exit-code HEAD --
test -z "$(git -C "$inferno_host/source" status --porcelain=v1 --untracked-files=all)"
test ! -e "$inferno_host/source/.git/objects/info/alternates"
```

Retain the exact commit, command logs and source tree. An ordinary clone does not
copy ignored firmware, build products or external tools; supply their pinned
paths in the runtime descriptor. It also does not make mismatching helper source,
profile, cache or disk lineage acceptable. The preparation validator must still
accept those inputs. Run all three phases from this same source location, using
fresh output directories and actual SHA-256 values from the preceding files:

```sh
"$inferno_host/source/companion/run" prepare-import \
  --ipa /external/Owned.ipa --runtime /external/runtime.json \
  --runtime-sha256 RUNTIME_SHA256 --output /external/NEW-PREPARED
"$inferno_host/source/companion/run" stage-import \
  --session /external/NEW-PREPARED/session.json --session-sha256 SESSION_SHA256 \
  --output /external/NEW-STAGE
"$inferno_host/source/companion/run" boot-import \
  --stage /external/NEW-STAGE/verified-stage.json --stage-sha256 STAGE_SHA256 \
  --session /external/NEW-PREPARED/session.json \
  --output /external/NEW-INSTALLED --seconds 1200
```

Run each next command only after the previous phase passes its documented gates.
The second and third commands each launch a VM; the first does not. Preparation
records its complete source hash set, and later validators recheck those bytes
at the retained source location. Clean Git checks are useful operator checks,
not a substitute for those session pins. Keep logs and products outside the
checkout, and use `PYTHONDONTWRITEBYTECODE=1` if inspecting Python entry points to
avoid incidental `__pycache__` files in the retained tree.

The host-only check in `evidence/durable-host-source-actual/` created a real local
clone at committed revision `3f8b2d5623a2ac862eba2899771049c44b197316`, verified
clean detached source and independent object storage, checked four existing
helper source pins, and resolved these three CLI help commands. It did not create
a session, stage an image, launch a VM, or move an existing source root.

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


### Assemble the local runtime descriptor

This complete structural template uses placeholders, not valid pins. Replace
all paths and SHA256 values with your retained artifacts; JSON accepts no
comments. Hash the resulting descriptor with `sha256sum runtime.json` for
`--runtime-sha256`. Do not copy another machine's paths, fabricate install logs,
or replace a missing provenance record with an assertion of success.

```json
{
  "schema": "inferno.local-ipa-runtime.v1",
  "inputs": {
    "profile": {"path": "/external/runtime/profile.json", "sha256": "PROFILE_SHA256"},
    "raw_ramdisk": {"path": "/external/runtime/ramdisk-payload.raw", "sha256": "RAW_RAMDISK_SHA256"},
    "probe": {"path": "/external/helpers/inferno-probe", "sha256": "PROBE_SHA256"},
    "disk_helper": {"path": "/external/helpers/inferno-prepare-root", "sha256": "HELPER_SHA256"},
    "helper_build": {"path": "/external/helpers/build.json", "sha256": "HELPER_BUILD_SHA256"},
    "hfsplus": {"path": "/external/tools/hfsplus", "sha256": "HFSPLUS_SHA256"},
    "clang": {"path": "/absolute/resolved/clang", "sha256": "CLANG_SHA256"},
    "linker": {"path": "/absolute/resolved/lld", "sha256": "LLD_SHA256"},
    "cache": {"path": "/external/runtime/launchd-cache.plist", "sha256": "CACHE_SHA256"},
    "base_report": {"path": "/external/stopped-base/report.json", "sha256": "BASE_REPORT_SHA256"},
    "emulator": {"path": "/external/build/qemu-system-aarch64", "sha256": "EMULATOR_SHA256"},
    "emulator_build": {"path": "/external/build/build-manifest.json", "sha256": "EMULATOR_BUILD_SHA256"}
  },
  "overlay_tools_root": "/external/overlay-tools",
  "tool_invocations": {
    "clang": "/absolute/invocation/clang",
    "linker": "/absolute/invocation/ld64.lld"
  },
  "cache_binding": {
    "basis": "reviewed-retained-lineage-not-fresh-guest-export",
    "base_report_sha256": "BASE_REPORT_SHA256",
    "cache_sha256": "CACHE_SHA256",
    "install_profile": {"path": "/external/cache-install/profile.json", "sha256": "INSTALL_PROFILE_SHA256"},
    "install_report": {"path": "/external/cache-install/run/report.json", "sha256": "INSTALL_REPORT_SHA256"},
    "install_serial": {"path": "/external/cache-install/run/serial.log", "sha256": "INSTALL_SERIAL_SHA256"},
    "cache_readback": {"path": "/external/cache-install/readback-launchd-cache", "sha256": "CACHE_SHA256"},
    "raw_ramdisk_preparation": {"path": "/external/recovery-preparation/preparation.json", "sha256": "PREPARATION_SHA256"},
    "lineage_evidence": [
      {"path": "/external/lineage/review.json", "sha256": "LINEAGE_SHA256"}
    ]
  }
}
```

| Field(s) | Required producer or retained evidence |
| --- | --- |
| `profile`, `raw_ramdisk` | Retained original-component profile accepted by `boot.load_profile` and its unwrapped recovery payload. [The plaintext recovery extractor](native-probe/RAW_RECOVERY.md) produces the raw payload for the supported pinned profile without changing its bytes. The preparation record below must bind both. This is not the new IPA recovery profile. |
| `probe`, `disk_helper`, `helper_build` | Compatible owned binaries and their actual build record. The validator requires `outputs.inferno-prepare-root.sha256` and `sources` pins matching the current four preparation source files. [The preparation-helper builder](native-probe/PREPARE_HELPER.md) now produces this record from an actual build; its first output matched retained helper60 byte-for-byte. The older `native-probe/build.sh` record format is not interchangeable. Do not hand-convert a record to pretend a build occurred. |
| `hfsplus`, `clang`, `linker`, `tool_invocations` | Existing local binaries with hashes; input pins name resolved regular files. Invocation paths must resolve to those files; retain `ld64.lld` as the Mach-O driver name even if its target is `lld`. |
| `emulator`, `emulator_build` | `companion/build-linux.sh` output and actual build manifest binding its binary. Keep its dependency/build tree. |
| `overlay_tools_root` | `python3 companion/disk_overlay.py bootstrap --tools-root /external/NEW-tools` produces pinned local tools/provenance for the tested platform. Existing valid tools may be reused. |
| `cache` | Retained original launchd cache with exactly one owned `org.inferno.app-probe` job. Preparation replaces that job only, preserving all other entries. |
| `base_report` | Eligible stopped overlay report with retained seven namespaces, immutable backing chain, hashes and KEEP records. Both recovery and installed child depth must fit; no failed attempt may substitute. See [BOOT.md](BOOT.md). |
| `install_profile`, `install_report`, `install_serial`, `cache_readback` | Actual original cache-staging artifacts: profile cache hash, report/profile binding and exit0, sibling serial log with unique zero-mismatch cache readback and completion, plus byte-identical readback. Produced by the earlier recovery preparation/run, not by this template. |
| `raw_ramdisk_preparation` | Actual `native-probe/prepare.py` preparation record whose `source_raw_sha256` and `source_profile` bind the selected raw payload/profile. |
| `lineage_evidence` | One to32 pinned retained records for reviewer-assessed ancestry from that installation to the selected base. Hash checks retain the selected history; they do not independently prove current guest cache contents. |

Durable preparation used this exact schema, checked all72 source pins and eight
HFS readbacks; see `evidence/durable-prepare-demo-1-actual/`. Its subsequent
recovery passed the separate raw/stopped checks. These are local-artifact
examples, not a distributable runtime or an automatic fresh-IPSW installation.

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

### Observe and operate a generic imported app

`boot-import` remains in the first terminal until the attempt ends. In a second
terminal, use the **same retained host tree**. Once `boot/command.json` exists,
read its private VNC endpoint; do not open a second QMP connection or a window on
the host display:

```sh
set -euo pipefail
inferno_host=/persistent/external/host-runtimes/RELEASE
attempt=/external/NEW-INSTALLED/boot
vnc_socket=$(python3 - "$attempt/command.json" <<'PY'
import json, sys
argv = json.load(open(sys.argv[1]))
assert isinstance(argv, list) and argv.count('-vnc') == 1
endpoint = argv[argv.index('-vnc') + 1]
assert endpoint.startswith('unix:')
print(endpoint[len('unix:'):])
PY
)
"$inferno_host/source/companion/run" observe --socket "$vnc_socket" \
  --output "$attempt/view-001" --observe-seconds 10
```

Review the captured PNGs before choosing any action. A first frame can be stale;
continuous observation can stimulate display refresh and is not presentation
latency evidence. See [headless display details](BOOT.md#headless-interaction-during-a-long-boot).
Every observation/action directory must be new. Wait for the current guest's
`INFERNO_HID_READY` serial banner before explicit touch input. Touch uses the
owned serial HID route, **not** `observe --tap` VNC pointer events. For a target
you have actually reviewed, coordinates are normalized integers0..32767;
choose `reviewed_x`/`reviewed_y` for the current frame, never reuse fixture
coordinates blindly:

```sh
"$inferno_host/source/companion/run" owned-control \
  --report "$attempt" --output "$attempt/tap-001" \
  tap "$reviewed_x" "$reviewed_y" --duration-ms 150
"$inferno_host/source/companion/run" observe --socket "$vnc_socket" \
  --output "$attempt/view-002" --observe-seconds 10
```

Lock screens or alerts may require separately reviewed actions first. For an
explicit swipe, `owned-control ... swipe X0 Y0 X1 Y1 --duration-ms 1500` uses the
same coordinate range. The generic imported launcher does not support the
fixture's `open` command or strict lifecycle/counter gates. Do not send repeated
input merely because the first acknowledgment arrived without a visible change.

Keep the before/after frames, raw serial, action submission and original process
listing. An ACK reports transport acceptance, not app callback or UI success.
After the intended observation is complete, an explicit normal end is:

```sh
"$inferno_host/source/companion/run" control --report "$attempt" finish-observation
```

Wait for the first terminal to exit and inspect its result. `completed-run.json`
only asserts normal shutdown; assess visible resource loading and interaction
separately. Failed or uncertain visual results must stay labeled as such even
if shutdown is normal. Do not use `finish-observation` to convert a failed
interaction into a successful journey. Run85 retained two observation windows
with Count0 after one ACK0 (`delivery=unproven`); no app callback was established.
Its operator interrupted the verified runner for forensic preservation, and the
wrapper retained `failure.json`/`INCOMPLETE.json`, not a completed result. No
failed output is a new eligible base. [The control contract](QMP_CONTROL.md)
and [owned journey guide](OWNED_JOURNEY.md) describe the underlying tools; their
fixture-only success checks do not apply to arbitrary imported apps.
