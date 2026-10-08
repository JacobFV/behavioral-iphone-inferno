# Persistent-source host preparation: actual first run

The ordinary persistent clone at revision3f8b2d5623a2ac862eba2899771049c44b197316
ran prepare-import once with the original owned demo IPA and runtime/helper60
pins. It completed in38.01s with exit0 and host-prepared-not-staged. Full runtime,
cache lineage, helper sources and base validators were enabled. No staging or VM
was run; no existing source tree, session or disk was changed.

Session: `/home/brandonin/.local/share/inferno/app-import/durable-prepare-demo-1/session.json`
SHA256: `faaa48f9b2f7a9f8f1b6f705e09c72a59c05c1025c7af7d355ed1a4af35ed044`.

Raw command/logs and HFS operations are retained here. `audit.py` independently
compares eight actual readback files byte-for-byte with source inputs, checks all
72 implementation pins at the persistent source location, checks the clean exact
revision, subprocess log hashes/exit codes and absence of failure markers.
`audit.json` records these results. Apple ramdisk/cache and generated executable
bytes remain outside Git. This is a host preparation result, not recovery
readback, installed eligibility, launch or general IPA compatibility evidence.

The earlier clone/CLI-only evidence remains unchanged. Future explicit staging
and installed boot must use this same retained source tree and ordinary gates;
this result authorizes no automatic VM or source relocation.
