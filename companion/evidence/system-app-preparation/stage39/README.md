# Stage 39: exact original HID class permission

Source is stopped app-boot-18 root SHA256
868fd033c50a409e793862ec760d56ac88d458e57e601e9e1ba9acac629414ea
and its six paired auxiliary namespaces. Boot18 found IOHIDResource but the
original type0 open returned0xe00002e2. Original Sandbox operation51's exact
class-array rule is documented separately in hid-mac-open-authorization-inspection.json.

Only owned /usr/bin/inferno-hid-input installed bytes change: 69,168 bytes,
SHA25689d623ff804b02bba4096df1a33f3ddef574c3c6ac720feadd7996b033954d36.
Candidate source f24dbaba7d adds only the singleton class permission
com.apple.security.iokit-user-client-class=[IOHIDResourceDeviceUserClient]
alongside the existing developer virtual-device Boolean. The exact prior helper
was re-signed with our ad-hoc signer, without recompilation. All file-backed
Mach-O sections and both object files are identical. The comparison and extracted
entitlement dictionary are retained here. No Apple identity or signature claim.

Original diagnostic wrapper flow, descriptor, properties, console protocol and
operator-only input behavior remain unchanged. Existing build42 readiness and
its identical535-byte loose descriptor were rewritten byte-identically because
the preparation interface requires them. No launchd cache, app, launcher,
unlock helper, firmware or operating-system policy change is part of this stage.

Actual recovery serial verifies HID69,168 bytes and readiness+job69,207 bytes,
both zero byte/mode/ownership mismatches. Both normal System unmounts completed,
followed by PREP_COMPLETE. Intentional host interruption after success invoked
the runner finally cleanup: QMP quit id6 acknowledged, emulator exit0. Seven
namespace hashes were calculated only after process completion. Stable archived
recovery binary was explicit. Final root SHA256:
29c65e9d70aefe2ff3c2cdea7bd3c04ff68540049c29fa7a0f07807fe825e03d.

This is preparation evidence, not proof that the normal API opens or creates a
virtual service. The next full boot must establish resource/open/Create/matching
results before separately authorized input. No gesture was issued in this stage.
