# Run62 stall observation, before subsequent Home

Archived emulator670 and unchanged predecessor stage50/HID54 produced an actual owned tap1 for boot984718F4-62F9-454E-BD9B-FB6F62EA548E/PID312. Exact TAP15010ea026d14556aedbeaa0a79215b8, down/up result0, ACK0, raw tap1 and validated relay identity are retained with physical byte references. Loopback claimed PID verification is not peer authentication.

All sixteen confirmation frames and nine subsequent traced-view frames independently hash to d4735b38cd6a0679deaaa3ff4709a9a6b0372df255ab9e127754fb8b4179a5d2. Parent reviewed this image as counter0. Captures are host-visible observations, not intrinsic presentation clocks.

Immutable guest-errors prefix ends12964; bracket[5800,12964) is7164 bytes. It contains21 output-ready events,19 status-W1C events (value/before0x400,after0) and57 unknown zero reads (38GP0x184,19main0x45004). There are **zero submits, BH, pipe or GP-configuration events**. Archived binary lacks the newer status-read event; W1C is not proof of the preceding returned read value.

All seven enables and seven deadline disables match raw QMP replies; final disable result1791331193.865935. No HMP/input QMP command appears in retained prefix, and no serial input occurred during the window. Both VNC observation reports contain no input events. The window started after the original tap/stall, so initial draw behavior is unknown. Continuous refresh can stimulate guest rendering.

SAMPLE is unsupported by this exact HID54 guest; no attempt was made. No causal emulator/HID revision conclusion follows from this one predecessor-state reproduction. This audit precedes and excludes the parent's later Home phase.
