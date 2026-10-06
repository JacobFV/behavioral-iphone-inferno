# Stage35: observation-only touch/GPIO registry helper

Source is immutable stopped app-boot-12 root SHA256
20a20cd1288df1bd556c0ff460a39b399f023c89e1918defd233ee09987eeb37
and paired auxiliary namespaces. Only the owned readiness binary and its same
535-byte loose job descriptor were staged. The cached job, app/launcher/wrapper,
single-unlock helper and all other configuration remain inherited.

Readiness now execs its own --touch-registry-once mode in a bounded child before
each existing process snapshot. It observes exact aop-gpio name and original
AppleHIDTransportDeviceSPI class, immediate parents/children, and only names,
classes, IDs, busy state and return codes. No properties, user-client calls,
power/interrupt changes, extra job or entitlements are involved. Existing process
and bounded crash observations continue. Source/import audit is under
companion/native-probe/ioreg-audit; all33 original-cache imports resolved.

Actual guest readback verified69,159 aggregate bytes: readiness68,624 plus loose
job535, with zero mismatches. Normal System unmount, INSTALLED and COMPLETE
followed. Intentional host stop received QMP quit acknowledgement and emulator
exit0. Stopped final root SHA256:
dd1062ad10cf09dc3b18f1c84d8bc2eb6d2d6ed2ff54bdc2c546284d44d403de.
All seven namespace hashes are retained. Recovery used archived original075b
emulator explicitly, avoiding concurrent trace builds. This verifies staging;
actual registry observations require the next full-system boot.
