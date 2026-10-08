# Actual unchanged consumer accepts newly built helper provenance

The persistent3f8b2d5623 source ran prepare-import with a NEW runtime descriptor
and fresh output. Only inputs.disk_helper and inputs.helper_build changed from
the known durable runtime; runtime-diff.json records exact old/new pins and
structural equality of every other field. The helper executable is unchanged in
bytes, while its new build record comes from the tracked producer's actual run.
No historical runtime, helper, session or source tree was edited.

Actual existing validation and all four subprocesses passed, publishing
`~/.local/share/inferno/app-import/rebuilt-helper-prepare-1/session.json`, SHA256
`aae8fd302f4a053c20e0ab6acb7de1ad0ac3be0ddfe211ffd47484b8fc825d9b`.
New runtime SHA256: `3a36be4381f808293b4aa328f92c01ed35fb2bac0868d913cacb3cafdd4d10d9`.

The independent audit rechecked all72 source pins at the persistent location and
eight actual HFS readbacks byte-for-byte, plus subprocess logs and clean source.
No incomplete/failure markers remain. Normal preparation performed its required
base validation; this audit did not duplicate backing hashes. Raw logs and HFS
operations are retained; binary/cache/ramdisk products stay external.

This is host-prepared-not-staged. There was no VM, recovery readback, installed
eligibility, app launch or visual success in this task. Consumer checks were not
relaxed or replaced with converted historical build evidence.
