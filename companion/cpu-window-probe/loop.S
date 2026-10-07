// Wholly owned AArch64 loop. No Apple implementation or SDK.
.global _start, probe_entry, probe_return
.text
_start:
 mov x1, #0x1234
 mov x2, #0x56
 bl probe_entry
probe_return:
 mov x4, #0x09000000
 ldr w5, [x4, #0x50] // PL011 unimplemented offset: tests guest_errors stays enabled
 mov x6, #0x20000
1: subs x6, x6, #1
 b.ne 1b
 b _start
probe_entry:
 mov w0, #0x789
 ret
