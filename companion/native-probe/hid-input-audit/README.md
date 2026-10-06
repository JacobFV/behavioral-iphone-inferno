# Original HID API and console input investigation

Current execution status: boot17 proved the private serial roundtrip, but virtual
Create returned NULL and no report was sent. Boot18 isolates this to original
IOServiceOpen(type0) returning0xe00002e2 despite IOHIDResource presence. See
`../../evidence/system-app-preparation/stage38/boot18-open-observation`. Earlier
sections below retain the research/candidate chronology; they are not runtime
success claims.

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

## Transport/parser implementation, backend deliberately unresolved

`hid-input.c` and `hid-input.h` implement only the bounded console protocol and
backend interface. Explicit `--console-operator-input` is required; no gesture is
created at startup. There is no shell or generic command execution. IDs are
remembered for the process lifetime; malformed lines and duplicates are rejected.
Limits are160bytes per line,32requests,32errors,7200seconds. SIGINT/SIGTERM/SIGALRM
request clean stopping. The original console termios is not changed.

The `INFERNO_HID_TRANSPORT_ONLY` compile mode returns explicit attempt status-100
and emits no events. No production backend or sender identity has been selected:
original backboard routing appears to require a recognized digitizer service,
which remains under investigation. This code has not been staged or run in iOS.

Validation: arm64-ios14 freestanding compilation with Wall/Wextra/Werror passed.
An external host harness tested accepted boundary inputs, rejected out-of-range/
trailing/malformed inputs and100,000 bounded malformed lines under GCC AddressSanitizer
and UndefinedBehaviorSanitizer, with no findings. Clang's host ASan runtime was
unavailable; GCC's installed runtime supplied this bounded parser check. These
checks establish parser behavior only, not serial connectivity or OS input.

## Reviewed normal virtual-device candidate

The candidate backend now uses original `IOHIDUserDeviceCreate` and
`IOHIDUserDeviceHandleReportWithTimeStamp`, not direct event dispatch. Apple's
IOKitUser-1726.140.1 `hid.subproj/IOHIDUserDevice.h/.c` supplies both declarations
and lifecycle semantics. Original recovery IOKit Create0x47df0 passes options0;
HandleReportWithTimeStamp0x49614 passes timestamp scalar and report bytes to
selector2. Normal options0 creates/starts the device immediately. Scheduling is
needed for Get/SetReport callbacks or StartWhenScheduled, neither used by this
input-only descriptor. No CFRunLoop scheduling is therefore requested.

Disk-agent original-kernel evidence establishes the singleton Boolean entitlement
`com.apple.developer.hid.virtual.device`. It leaves Privileged=false and marks the
device HIDVirtualDevice=true. Reserved IOClass/IOProviderClass/IOUserClientClass/
IOKitDebug properties are not supplied. IOHIDEventService propagates ordinary
provider `Built-In` Boolean without a privilege branch. This candidate's honestly
named `Inferno Operator Touchscreen` is explicitly Transport=Virtual and describes
its integration with this VM's display using Built-In=true, no external UUID.
There is no Apple vendor/product ID, original service identity, senderID or
contextID override, and no manager/admin/directdispatch entitlement.

The self-authored standard descriptor is a TouchScreen Application with one
Finger logical collection: tip/in-range/confidence bits, padding, contactID,
X/Y logical0..32767 and contactCount. It defines seven input bytes, no output or
feature reports. The original generic driver normalizes the coordinates. Original
IOKit service initialization recognizes TouchScreen usage and its event callback
sets display-integrated field0xb0019 if absent, so no guessed extra field property
is needed. Descriptor host structure/hash is recorded separately; actual guest
parsing and UI delivery are not yet established.

The server creates the virtual service at startup without sending a contact
report. It logs actual returned registry ID, class and bounded immediate children.
Per explicit operator command it checks at most64 descendants for a real
IOHIDEventService (at most5seconds of polling), never queues/replays a failed
request. It reports down, bounded interpolated moves for swipes, then always
attempts a zero-contact release, including controlled stop/error paths. SIGINT,
SIGTERM and the7200-second alarm request clean stopping. Report logs contain
actual mach timestamps and original return codes; ACK still means attempt only.
CFRelease closes the owned virtual device on normal exit.

Existing readiness spawns this separate helper only if its exact owned path
exists, using fresh exec; observation intervals and registry/ps/crash snapshots
continue. The child cannot execute arbitrary commands. The existing launchd job
and cache need no changes. Staging adds the owned helper and updates readiness,
with normal byte+metadata comparisons and unmount checks. No staging or guest
input execution is claimed by this candidate commit.

Latest audit resolves15 actual bind/lazy imports and18 dynamic symbols through
original cache export tries/reexports. SDK-free iOS compilation and signed
entitlement extraction passed. Parser ASan/UBSan checks passed again. Exact audit
outputs accompany this file; helper/build/artifacts remain external.

### Boot 17 creation diagnostics candidate

Boot 17 reached the owned parser through the serial transport, but both startup
and the single operator request saw original `IOHIDUserDeviceCreate` return NULL.
No input reports were emitted. The next candidate keeps that original wrapper
and the same 77-byte descriptor/properties/entitlement, adding a bounded preflight:
match `IOHIDResource`, print its actual class/registry ID, open its original type-0
userclient using the current task, print the actual return, then close and release
it. It calls no methods on this diagnostic connection.

Original recovery IOKit at 0x47ebc–0x47ef4 performs this same match/open sequence;
the wrapper's later create/start selector and analytics allocation failures remain
possible if the diagnostic open succeeds. The candidate deliberately does not
reimplement the create selector. `HIDOpenReportDescriptor` and its close function
are absent from original System IOKit's export trie/reexports. The helper logs
parser export presence and `parser_invoked=0/result=unavailable`; this is not an
OS descriptor acceptance result.

Build 43 compiled with `-Wall -Wextra -Werror`. Original cache audits resolve all
16 bind/lazy imports and 22 required dynamic symbols. The extracted ad-hoc
entitlement remains exactly `com.apple.developer.hid.virtual.device=true`.
The only proposed installed change is the HID helper (68,976 bytes, SHA256
`c1e93f41382f13cfbd4348cf0bf4ab6216c4a45c164d2855d616f9fb502c31bf`).
Existing readiness, app, jobs, and firmware stay byte-identical for this comparison.


### Entitlement-only candidate after boot 18

Original Sandbox operation51 evaluates `iokit-user-client-class` against the
caller's `com.apple.security.iokit-user-client-class` entitlement string array;
the traced terminal denial names that exact key. The developer virtual-device
Boolean admits the driver-specific initialization but does not replace this
outer class gate. The candidate adds only the singleton class array
`[IOHIDResourceDeviceUserClient]` alongside the existing Boolean. It does not
add manager/admin permissions or change an operating-system policy.

Build44 is a copy of the exact build43 executable re-signed with the owned
ad-hoc signer; no compilation occurred. All file-backed Mach-O sections and both
compiled object files are byte-identical. The 6,180-byte __TEXT,__text SHA256
remains `5c8b0b4357e4b5d2f902312679c053d1cc6a76c7daab7a1db55fc0c057617408`.
The only bytes differing before the signature are offsets1168/1169 (__LINKEDIT
file size) and1556/1557 (LC_CODE_SIGNATURE size). The signature begins at67600
in both. The extracted two-key entitlement dictionary and all comparisons are
in entitlement-only-audit.json. Original import audits remain16/22 passed.
Candidate is69,168bytes SHA256
`89d623ff804b02bba4096df1a33f3ddef574c3c6ac720feadd7996b033954d36`.
This is a prepared candidate, not proof of successful OS opening or input.
