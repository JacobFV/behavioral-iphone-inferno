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
