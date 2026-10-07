# Opt-in imported app recovery staging

Requires disk_path's `app-import.py` exposing `validate_import_manifest`. `prepare.py` re-runs the importer against its retained IPA and extracted bytes before generating a fixed binary copy plan. It independently pins manifest/tree hashes, identity, modes, paths, exact inventory, bounds and source IPA. No imported code is signed or rewritten.

New arguments:

```
--disk-helper-existing --imported-app-manifest /external/import/manifest.json
--imported-app-manifest-sha256 EXACT_MANIFEST_SHA256
```

The first identical fixture proof additionally requires:

```
--allow-identical-fixture-tree-sha256 697b73b118021ae7f225a9ed65009e6ca0aa91c62a2b430e60e7d2b648370125
```

Only this explicit pin plus exact InfernoProbe.app / org.inferno.companion.probe identity permits an existing target. The guest must compare its entire existing bounded bundle byte-for-byte and mode/uid/gid against the imported source before copying anything. Different bytes or extra entries reject. All other existing targets reject, including other owned apps. No general overwrite mode exists.

The ramdisk contains `/usr/share/inferno-imported-app` and its fixed binary `.plan`. Every supplied file and the plan are extracted back from HFS and verified before guest use. Plan ABI is408-byte header and528-byte records, little endian,4096 entries,128MiB total,64MiB per file,511-byte relative paths/depth16. The guest validates the entire source regular-file/directory inventory and metadata, creates a fresh destination, copies each listed file, recursively compares bytes and metadata, syncs and attempts a normal unmount even on staging failure. Failed copies remain only on the disposable preparation disk; no rollback or successful install is claimed.

The existing fixture paths/defaults remain unchanged. Rebuild only `inferno-prepare-root` with its existing entitlements; the new included C code requires no new imports. `build.sh` records the added source hashes. ARM64 compile syntax is checked, but no guest staging/build execution is asserted by this evidence. The actual host integration check uses the imported byte-identical app22 fixture74976 bytes plus954-byte Info.plist. Its explicit plan totals75930 bytes. Negative checks reject wrong pins, extras, changed bytes and symlinks on temporary host copies.

This route stages files only. First fixture proof reuses the existing exact launcher/cache/job unchanged. Generic apps require separately reviewed manifest-driven original LaunchServices registration and a cached launchd job; the existing fixed fixture relay/OPEN path does not silently become generic. Import validation, preparation readback, launch acceptance and visible app behavior are separate milestones.
