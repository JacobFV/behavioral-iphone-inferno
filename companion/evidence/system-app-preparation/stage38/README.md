# Stage 38: original HID resource/open diagnostics

Source is stopped app-boot-17 root SHA256
0f3cbf476afa0e1842a2cc477ca658c6e518c599fda112be30f9c62019f30015
and its six paired auxiliary namespaces. Boot 17 proved the private serial
roundtrip but the original virtual-device Create returned NULL; no HID reports
were emitted. This stage prepares an observable original-resource open check.

The only changed installed bytes are owned /usr/bin/inferno-hid-input:
68,976 bytes, SHA256
c1e93f41382f13cfbd4348cf0bf4ab6216c4a45c164d2855d616f9fb502c31bf.
Source commit 453e802ac6 adds resource matching/class/registry ID and original
type-0 IOServiceOpen/current-task and IOServiceClose results before unchanged
Create. No diagnostic userclient methods are called. The original parser export
is unavailable and no descriptor acceptance result is invented. Descriptor,
properties, singleton developer virtual-device entitlement, serial grammar and
explicit-operator-only input behavior are unchanged.

The existing build-42 readiness helper and identical 535-byte loose descriptor
were rewritten byte-identically because preparation requires them. Their SHA256
values remain 3c360cba34c8d7616fc1ac173af4e7ebd21226f69addc9f11a2fcd6c0e8bcba1
and 238154a9609e05208acfb9e9c64570e8ea7831119a72c3f46d2c27c2a1a5fb91.
No launchd cache, app, launcher, unlock helper, or firmware changes were requested.
Build43's other rebuilt artifacts were NOT used for this stage; preparation.json
records the exact build42 preparation helper inputs.

Actual recovery serial records HID readback 68,976 bytes and readiness+job
69,207 bytes, both zero byte/mode/ownership mismatches. Both normal System
unmounts completed, then PREP_COMPLETE. Intentional host interruption after
success ran the runner finally cleanup: QMP quit id6 acknowledged and emulator
exit0. All seven hashes were calculated only after process completion.
Final root SHA256:
78de9f6dc03f5481f6f8428997eb6f205c044ad7dc5a87f9b21ed2d1c64fc161.

The archived stable recovery binary was explicit. This staging result does not
claim original IOHIDResource presence, successful userclient opening, virtual
service creation, report delivery, or a visual response; the next full boot
must establish those separately.
