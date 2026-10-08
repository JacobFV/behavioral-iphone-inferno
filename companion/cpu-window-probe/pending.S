// Wholly owned register/branch fixture. No Apple instructions or memory copied.
.global _start, probe_null, probe_active, probe_queued
.text
_start:
 mov x0, #0x125
 mov x1, #0x124
 mov x11, #0
 cbz x11, probe_null
 b active_case
probe_null:
 mov x10, #0x777 // Deliberately meaningless at null site; parser must ignore it.
 b active_case
active_case:
 mov x0, #0x126
 mov x1, #0x124
 mov x11, #0x1000
 movk x11, #0x4000, lsl #16
 mov x10, #0x126
 b probe_active
probe_active:
 mov x8, #0x2000
 movk x8, #0x4000, lsl #16
 mov x9, #0x127
 mov x11, #0x127
 cmp x9, x11
 b.ne delay
probe_queued:
 mov x4, #0x09000000
 ldr w5, [x4, #0x50]
delay:
 mov x6, #0x20000
1: subs x6, x6, #1
 b.ne 1b
 b _start
