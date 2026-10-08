# Fresh SEP/keybag recovery stage

`stage-sep-keybag.py` consumes a hash-pinned successful `grown-data.json`, validates
its actual original-API growth log and pre-finish prefix, normal shutdown, frozen
seven-file state and depth-two 32 GiB backing. It also reuses the reviewed growth
input validator to bind the flattened verified Data predecessor and its exact
auxiliary pairing. Growth provides two System fingerprints, **not** a fresh
postgrowth whole-Data verification.

Use `python3 companion/stage-sep-keybag.py --help` for path/hash arguments. The
helper must be the existing reproducible general preparation build, not the
separate growth executable. The fixed SEP payload and its extraction record are
additional pinned inputs. The selected profile's whole IPSW hash, unchanged SEP
ZIP member and n104ap Research Developer Erase Install BuildManifest SHA384 must
match. ZIP streaming here checks accessible original bytes; it performs no
key extraction, decryption, ticket generation, signature forgery or SEP rewriting.

The ramdisk job is exactly:

```
inferno-prepare-root --disposable-root-copy --existing-volumes --copy-sep --create-keybag
```

The coordinator extracts and compares ramdisk helper, probe, job and SEP input
before launching one private/headless recovery. It adds no guest C changes or
grants. It rejects any additional preparation mode. In particular, it does not
seed again, verify Data, install helpers/apps, or separately initialize gigalocker.
The keybag branch already invokes the original initializer.

Raw gates require discovery of six existing volumes; writable Preboot copy and
clean unmount; exact xART-writable/Preboot-read-only/Data-writable mounts;
original gigalocker init and SEP load status0; effaceable query0/formatted0/count1,
format0 and recheck0/formatted1; fresh MKBCreate status0/stat0/nonempty regular
file; original gigalocker shutdown0; ordered Data/Preboot/xART normal unmounts;
and KEYBAG_COMPLETE/PREP_COMPLETE. Already-formatted state and existing-bag -4
are rejected even though the general helper supports them. No bag contents are
logged. The simulated backend's loader messages are not real SEP security proof.

After exact checkpoint validation, the coordinator issues one normal finish,
requires ordinary QMP/emulator shutdown and source/ancestor stability, freezes
only its seven fresh output files, preserves them and validates depth three.
Private umask077 applies to all new outputs. Failure retains evidence and cannot
publish `sep-keybag.json` as success. There is no automatic retry.

The successful result is `fresh-keybag-created-not-runtime-ready`, with
`sep_destination_bytes_verified:false`, `postgrowth_full_data_verified:false`
and `ipa_runtime_ready:false`. Ramdisk input readback is real; the unchanged
general helper **does not compare SEP destination bytes**. Copy/loader/API path
success is not a destination hash, first unlock, installed boot, Setup or app
claim. Further destination verification requires a separately reviewed step.

Historical parser replay combines two explicitly identified old execution
fragments to exercise the new combined path; it is **synthetic composition**,
not a new VM execution or new initialization result. Real execution remains a
separate reviewed milestone.
