# Actual63 Home caller window

Bounded delta[62449,76767) contains18 matched status-read/W1C pairs, all0x400 and W1C after0;20 output-ready events;54 unknown MMIO reads and54 caller records; zero submits/BH/pipe/config writes. All nine enable/disable responses match actual QMP. No HMP or serial input occurred in the window. Explicit F6 down/up at1791332287.000713/2287.1508098 is preserved in the VNC report.

The same-attempt stderr reports slide0; original kernel hash verified. Existing parser8240bd63a4 classifies36 GP calls as decompression_failure and18 main45004 calls as interrupt_handler_ready_gate. No FIFO accessor caller is observed. Caller offsets in callers.json are relative to the retained delta; add62449 for original guest-errors offsets. Exposed LR/PC establishes this static call-site correlation, not subsequent internal ready-bit/object/callback completion.

Actual lifecycle records show samebootC9E86568-D530-4FD8-B231-D37893D85D74/PID245/main2600439612 resign8/background9. Both Home captures and all16 later confirmation captures independently hash to714e9ee5…, which parent reviewed as unchanged counter0. The confirmation connection1791332326.1752262–2347.3527658 extends beyond the trace-after checkpoint2327.31404 and is separately retained as later visual corroboration. QMP probe-before/0010/0014 PPM hashes likewise match independently. No frame timing or compositor-consumption claim follows.

No input, guest action, build or source mutation performed by this audit. Raw current-input evidence is distinct from original static branch reasoning and any later x21 diagnostic proposal.
