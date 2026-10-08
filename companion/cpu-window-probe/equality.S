// Wholly owned TB fixture. No Apple implementation bytes or memory copied.
.global _start, probe_mode, probe_equal, probe_false, probe_true, probe_return
.text
_start:
 mov x8, #0
 cbz x8, probe_mode
 b _start
probe_mode:
 mov x8, #253
 mov x9, #253
 cmp x8, x9
 b.ne _start
probe_equal:
 mov x8, #0
 tbnz x8, #0, probe_true
probe_false:
 b set_true
set_true:
 mov x8, #1
 tbnz x8, #0, probe_true
 b _start
probe_true:
 bl owned_status
probe_return:
 mov x4, #0x09000000
 ldr w5, [x4, #0x50]
 mov x6, #0x20000
1: subs x6, x6, #1
 b.ne 1b
 b _start
owned_status:
 mov w0, #0x2d5
 movk w0, #0xe000, lsl #16
 ret
