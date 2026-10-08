# Actual preparation with both reproduced inputs

The unchanged persistent3f8b2d5623 prepare-import consumer accepted the newly
extracted raw recovery file and newly built owned helper/build record together.
A NEW descriptor differs from the preceding rebuilt-helper descriptor ONLY in
inputs.raw_ramdisk.path; its hash, profile and all retained provenance are
unchanged. Before execution, the original preparation record's source_raw_sha256
and source_profile were checked against the selected payload/profile. No record
was rewritten or binding relaxed.

Actual output: `~/.local/share/inferno/app-import/reproduced-inputs-prepare-1`.
Session SHA256: `7c9c7fde80f09dcc6f45c026061f35ee02c07f26ef251d15868df244ac9877bf`.
Runtime SHA256: `52a1297061096d0d0a8936127e58e3e69f5629415514580a057971e5aca5ee76`.

All four subprocesses exited0. Independent audit checked72 source pins at the
persistent source tree, clean committed source, eight actual HFS readbacks
byte-for-byte and raw log hashes; no incomplete/failure markers remain.
The consumer's required runtime/backing validation ran normally, without a
separate duplicate disk-hash audit. Exact descriptor diff, command/logs and HFS
operations are retained here; binaries/filesystem data remain external.

This is host-prepared-not-staged, not a new installed runtime or guest success.
No VM, staging, firmware acquisition, old session/source mutation, signing of
Apple components or replacement of historical evidence occurred.
