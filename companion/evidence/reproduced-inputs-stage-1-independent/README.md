# Reproduced-input recovery stage: independent audit

PASS for stopped recovery eligibility only, not installed/app success.
The existing raw audit rechecks the exact new session7c9c7fde...9877bf,
persistent3f8b2d5623 source pins, fixed recovery command/profile and all raw
readback records. Content checkpoint precedes the sole normal finish; raw QMP
shutdown/exit0 precedes freezing only the new seven namespaces. Their present
identities agree with freeze and retention hashes; ancestors remain unchanged,
KEEP binds the new root, and runner/emulator PIDs are absent. No failure markers.

Verified-stage SHA256:
0767c38eabc0bdbb9a17a09c61a82e5c69951b972c7d1c81d119e7567461a57c.
The inputs contain the reproduced raw recovery and byte-identical rebuilt helper
with its new actual build record. No historical provenance was rewritten.
`audit.py`/`result.json` retain raw byte offsets/hashes and exact controls. No
additional full disk hashes, VM actions or metadata/source mutation occurred.
