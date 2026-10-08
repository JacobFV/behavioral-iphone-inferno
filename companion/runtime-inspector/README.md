# Fixed read-only runtime cache observation

This phase consumes a normal, retained `sep-keybag.json` result. It mounts only
System read-only on a disposable fourth overlay layer. It exports the original
`/System/Library/xpc/launchd.plist` (maximum 2 MiB) and computes the full SHA256 of
the fixed 2,052,489,216-byte arm64e dyld cache. The dyld cache is never exported.
No cache patch, launchd merge, signature edit or runtime installation occurs.
The resulting child is observation evidence, **not a runtime base**.

Keep the supplied firmware, disks, build outputs, serial export and reconstructed
Apple configuration outside Git. A fresh initialized tuple is not yet an IPA
runtime: later cache preparation, installation, original setup and an actual app
journey remain separate requirements.

`build.py --help` describes the pinned clang, Mach-O linker and ldid inputs. It
builds and ad-hoc signs only `inspect.c`, using the owned SHA256 implementation
already used by the cache patch helper. Sources must be committed and unchanged;
all commands, stdout/stderr, tools and entitlement readback are retained in NEW
external output. It does not boot a guest.

`stage.py --help` describes the pinned profile, plain recovery extraction record,
keybag result, inspector build, marker, HFS tool, emulator and overlay-tool inputs.
It replays the predecessor's raw completion and stopped seven-file lineage through
`keybag_state`, prepares a recovery image and reads back the exact helper, marker
and fixed job. It requires 2 GiB free before preparation and again before boot.
One bounded recovery runs with no UI input. Only a complete contiguous launchd
export, matching full hash, dyld hash and original clean System unmount permit the
single normal finish request. The final result additionally requires normal QMP
shutdown, unchanged sources/inputs, frozen new disk files and ordinary retention.
Existing ancestors are never chmodded. A timeout or failed gate retains failure
and incomplete markers; there is no automatic retry or promotion.

`export.py --serial PATH --serial-sha256 SHA --output NEW_EXTERNAL_DIRECTORY`
reconstructs an already completed fixed-file stream without launching a VM. It
rejects missing/duplicate/gapped chunks, incorrect byte counts or hashes, failed
unmount/result, oversized files and unsupported launchd dictionaries. A valid
export alone does not establish normal stopped recovery; `stage.py` records that
separately. The exported plist remains external even when host evidence is
committed. Guest marker text has no cryptographic session nonce: its attribution
rests on the fresh runner, pinned helper/job and retained raw command/serial/QMP
chain, not on the marker's name alone.
