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
Run75 exercised the manifest-configured helper with the distinct ImportedDemo
app: original process listing, reviewed bundled resource text and counter0→1.

An uninstrumented app uses a normal disk boot with the control mailbox and HID
serial input, without `--probe-journey`. Preserve original process listings and
reviewed VNC/periodic QMP frames as execution evidence. After observation,
`companion/run control --report ATTEMPT finish-observation` requests normal
runner cleanup and QMP shutdown. This command asserts no app or journey success
and is rejected when a probe journey is active; its existing completion gate
still applies. Run75 completed this uninstrumented guest journey and normal shutdown; retained
visual evidence is in `evidence/ipa-demo-75-visual/`. This single app does not
establish general compatibility or resolve the intermittent display freeze.
