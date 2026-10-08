# Flatten a verified Data stage without changing its contents

`flatten-verified-data.py` is a host-only operation. It accepts a pinned
`data-verified.json`, replays the actual initial-volume, seed and read-only
verification logs, and checks their normal stopped reports, original checkpoint
prefixes, sole finish requests and seven frozen namespace identities. It requires
the original 8 GiB raw ancestor and the expected four-layer chain. Failed,
incomplete, forensic, merely seeded or unrelated inputs are rejected.

Run with a new external output directory:

```sh
python3 companion/flatten-verified-data.py \
  --data-verified /absolute/verification-stage/data-verified.json \
  --data-verified-sha256 REPLACE_WITH_ACTUAL_HASH \
  --overlay-tools-root /absolute/disk-overlay-tools \
  --output /absolute/new-flattened-data
```

The hash option is `--data-verified-sha256` (use the exact manifest hash).
No conversion has been demonstrated by merely compiling this tool or invoking
its help. Actual execution must retain `convert`, `raw-info` and
`logical-compare` commands, return codes and unmodified stdout/stderr.

The tool requires space for the entire logical raw size plus 2 GiB. It uses the
existing pinned qemu-img to convert the top overlay into an exclusively new raw
file, then requires qemu-img logical comparison status zero. It checks primary
and backup 4 KiB GPT CRCs and equal partition tables, hashes the complete raw,
and revalidates all original source hashes and metadata after conversion. It
fsyncs and freezes only that new raw file, once, and writes the existing
`KEEP-OVERLAY-BACKING.json` schema. It never grows the disk, resizes APFS, launches
a guest, deletes ancestors or changes their metadata.

`flattened-data.json` retains both source-chain verifications, exact six paired
auxiliary references and the original verified report/retention hashes. Future
boot arguments use the new raw with `--root-image`, its full hash,
`--root-overlay` and **the same verified stage's `--auxiliary-state`**. The
auxiliary namespaces must never be replaced with blank files. All original
artifacts remain retained. Consumers must reject output directories containing
`INCOMPLETE.json` or `failure.json` and validate current raw and auxiliary pins
before use; the result is not itself a fabricated boot report.

The result remains `flattened-verified-data-not-runtime-ready` with
`ipa_runtime_ready: false`. It inherits only the original read-only Data comparison
scope (bytes, modes, ownership, symlinks and missing/extra entries), not xattr,
ACL, timestamp, compression, keybag, setup or app-readiness claims.
