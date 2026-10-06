// Owned SDK-free Darwin arm64 recovery probe. No Apple SDK; guest libSystem provides loader bootstrap.
.section __TEXT,__text,regular,pure_instructions
.globl _start
.p2align 2
_start:
    mov x16, #20 // getpid
    svc #0x80
    mov x19, x0
    adr x1, message
    adr x2, message_end
    sub x2, x2, x1
    mov x0, #1
    mov x16, #4 // write(stdout, marker, length)
    svc #0x80
    mov x0, #0
    mov x16, #1 // exit(0)
    svc #0x80
    brk #0
message:
    .ascii "INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls\n"
message_end:
