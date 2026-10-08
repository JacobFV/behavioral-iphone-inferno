# Fresh runtime artifact preparation

`python3 companion/prepare-fresh-runtime.py --input ABSOLUTE_JSON --input-sha256 SHA256 --output NEW_EXTERNAL_DIRECTORY`

The input schema is `inferno.fresh-runtime-artifact-input.v1`, with exactly
`schema`, `inputs`, and `policy`. Policy must be
`disable-five-unsupported-services`. Inputs are exact `{path,sha256}` pins named
`inspection`, `keybag_stage`, `runtime_build`, `prepare_build`, `app_manifest`,
and `launcher_build`. The last is the existing manifest-bound launcher's
`build-evidence.json`, produced by `app-probe/build-import-launcher.py`. Rebuild
that owned launcher separately if its recorded sources no longer match.

This first producer accepts only the actual owned ImportedDemo identity/path.
It revalidates the importer tree, unchanged helper output/source pins, and exact
launcher target. It reconstructs the fresh original launchd configuration from
the stopped inspector's raw serial and binds its same-keybag predecessor. It
inserts readiness, empty-secret unlock, and the actual imported-app launch job
using the existing merger's `--job`; it does not replace historical installed
jobs. Exactly five documented original services receive `Disabled=true`. No
signature file is supplied or modified. Independent merge comparison rejects
any other configuration change.

The output is **host-prepared-not-staged**, never a runtime manifest. Its prepare
argument fragment deliberately omits profile, ramdisk, base and output: the
future stage must independently validate the renderer result from this same
keybag lineage and add the exact recovery inputs. This producer reads no disks,
performs no full disk hashes, copies no ramdisk/dyld cache, and starts no VM.
Inspector metadata/raw/source binding here does not replace the future stage's
full stopped-disk validation. Original migration, first unlock, Setup and actual
app rendering remain unproven for this fresh lineage.

Only host merge negatives and CLI parsing have been exercised at source review;
no actual inspector-based artifact production or guest installation is claimed.
