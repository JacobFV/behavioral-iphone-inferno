# Original HID API and console input investigation

Read-only findings, not successful input execution. SPI firmware validation
remains failed as documented in stage36/boot16-loader-observation. An original
OS event-dispatch route would be a distinct automation mechanism, not proof the
hardware transport works.

Original recovery IOKit exports IOHIDEventCreateDigitizerEvent at0x24588,
IOHIDEventCreateDigitizerFingerEvent at0x24800, IOHIDEventSystemClientCreate at
0x32dcc and IOHIDEventSystemClientDispatchEvent at0x33e60. Default Create passes
client type3 into CreateWithType; it avoids assuming a different modern signature
for the three-argument create function. DispatchEvent serializes via
IOHIDEventCreateData and __IOHIDCreateBinaryData, then calls the original Mach
io_hideventsystem_dispatch_event with the client's port. It has no usable delivery
result (cleanup ultimately calls CFRelease); visual observation must establish
that an input reached its target.

Apple-authored WebKit IOKitSPIIOS.h provides exact original-style C declarations:
IOHIDFloat is double; generic digitizer arguments are allocator, timestamp,
transducerType,index,identity,eventMask,buttonMask,x,y,z,pressure,twist,range,touch,
options. Finger omits transducerType and buttonMask. Integer fields/masks are
32-bit; range/touch boolean_t are integers. Original disassembly uses five double
registers and the matching integer argument shifts in the finger wrapper.

Relevant declared values: digitizer event type11; hand transducer3, finger2;
range mask1, touch2, position4, identity32, cancel128; field base11<<16;
display-integrated field0xb0019. The WebKit generator constructs a hand parent,
sets display-integrated=1, appends finger children, and changes masks for
start/move/end/cancel. Its final dispatch is app-local UIApplication enqueue with
a contextID, so that source alone does NOT prove global DispatchEvent coordinate
routing or context behavior. Those require original global server investigation.

Independent disk-agent trace identifies exact normal-client dispatch entitlement
com.apple.private.hid.client.event-dispatch. Recovery server bit3 check at0x6512c
and installed System equivalent0x181338134 gate the request; denied requests can
still return0. This is another reason acknowledgements cannot claim delivery.
No admin client or broad entitlement is proposed.

## Private serial transport candidate

Original-era primary XNU source shows /dev/console cnread delegates to constty or
default km_tty; kmread invokes line discipline l_read. kmopen initializes normal
TTY defaults. serial_keyboard_poll feeds cons_cinput, which invokes l_rint.
SERIALMODE_OUTPUT=1 and INPUT=2, so existing serial=3 enables both. An O_RDONLY |
O_NONBLOCK console reader with newline-delimited ASCII can use canonical input
without mutating termios. Actual guest roundtrip is still untested.

Agreed bounded proposed grammar with the runner owner:

    INFERNO_HID_V1 <32-lowercase-hex-request-id> TAP <x> <y> <duration_ms>
    INFERNO_HID_V1 <32-lowercase-hex-request-id> SWIPE <x0> <y0> <x1> <y1> <duration_ms>

Integers only; normalized coordinates0..32767, duration1..2000ms; newline and
maximum160bytes. Reject malformed/duplicate requests, no automatic replay or
queued retry, no arbitrary commands or shell. Create normal client only on an
explicit request after host observation of UI readiness. ACK indicates an attempt,
not OS delivery. A gesture implementation must finish with finger release and
cancel/release on controlled interruption. No implementation/staging is recorded
by this audit.

## Existing manifest inventory

Read-only complete IPSW member-name scan found only BuildManifest.plist among
manifest/ticket/.im4m/.img4 patterns; known verified-profile and range-inputs
inventories likewise contain no provided personalization ticket or IMG4 manifest.
BuildManifest is component metadata, not a signed IM4M. This is a bounded inventory
finding, not an assertion that no genuine manifest exists anywhere.
