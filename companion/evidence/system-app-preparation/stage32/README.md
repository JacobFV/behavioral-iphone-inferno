# Stage32: narrow owned-helper permission declaration

This preparation cloned stopped stage31 and its paired six auxiliary namespaces.
The only requested staged file was our /usr/bin/inferno-unlock-empty. Its code
object is byte-identical to build36; build37 adds only the original driver's
required Boolean com.apple.keystore.device entitlement to our own ad-hoc
signature. The extracted entitlement is retained here. App, launcher, wrapper,
launchd cache and observer were not replaced.

The raw serial records a 67,600-byte helper readback with zero mismatches, normal
System unmount, and INFERNO_PREP_COMPLETE. Intentional runner termination then
received an acknowledged QMP quit with emulator exit0. attempt_completed=false
reflects that early host stop. This is verified preparation, not an app journey.

Build37 ran before its final source commit; each recorded source hash was checked
against committed 8f64929592. The manifest therefore truthfully retains the older
HEAD alongside this final source verification. Binaries and disk products remain
outside Git. Boot8 results are recorded separately under migration-first-unlock.
