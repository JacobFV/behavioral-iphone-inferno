# Stage33: isolated dictionary-registration launcher candidate

Source is immutable stopped stage32, SHA256
34240b9546eaea73e1ddae0997a194f1ba9c23e5302d3fb76abf69a35675e276,
with its paired auxiliary namespaces. Only the owned /usr/bin/inferno-launcher
was replaced, using the dictionary registration candidate SHA256
bae364e5449af63f9647acc6e3bd0e41f2f5752b285b5ee688c468b5071c44cd.
The original own app Info.plist plus Path are the registration dictionary;
no additional identity or entitlement fields are supplied. Wrapper, app,
launchd configuration and entitled single-unlock helper remain inherited.

Actual serial records 68,016-byte launcher readback, zero mismatches, normal
System unmount and PREP_COMPLETE. Intentional early stop received QMP quit
acknowledgement and emulator exit0. All seven stopped namespace hashes are
retained. Final root SHA256 is
31f1f5c21b49f7d5f892a21361e2d646829f3eca9d3949e12fbd18af5c6a0941.

This verifies staging only. No dictionary registration or app execution success
is asserted. The independent first simulator protocol comparison must still use
unchanged stage32. Build metadata records its own build-time source state;
launcher source and original-export import audit are owned by app-probe.
