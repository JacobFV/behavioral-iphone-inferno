# Actual boot-import demo1 / installed run81

Independent PASS of the wrapper contract. No VM/control or disk mutation by this
reviewer. `audit.py` rechecks small-file source/input hashes, exact fixed argv,
retained metadata snapshots and generic report/normal-result gates. It compares
the stored stage bindings with the fresh verification recorded at launch without
repeating namespace/backing hashes.

The wrapper used session2 and coordinated-stage-demo-2 exactly. Its sibling runner
and control match that session's baseline pins. The installed profile is the
original profile, not the generated recovery profile; no initrd is used. The
fresh overlay is paired with the stage's six auxiliaries through the original
loader. There were no input or diagnostic overrides in wrapper argv.

Actual completed-run equals the independently recomputed normal result, including
stable inspected report/QMP identities. One operator finish-observation precedes
the normal raw QMP quit/host shutdown. Wrapper3822053, runner3822649 and
emulator3823050 are absent; INCOMPLETE/failure markers are absent. The completed
result correctly retains `app_execution_asserted:false` and is not a new eligible
base. No disk freezing was performed by the wrapper or this audit.

Separate bounded raw corroboration: original ps lists
`256 1 501 Ss /Applications/ImportedDemo.app/ImportedDemo`. The one named counter
request d8fd4385289a441fbf52efa8e939151e has matching mailbox, serial wire,
68-byte transmission, original down/up results0 and ACK0. Its transport expressly
does not assert UI delivery. Root separately reviewed bundled text and counter0→1;
this audit does not classify pixels. Raw references are in operator-records.json.

No repeated firmware/namespace/backing hash pass was needed. The runner's actual
pre/postflight and stage verification remain their own recorded evidence. The
success here is the integrated wrapper execution with normal cleanup, alongside
separate root visual evidence, not general IPA compatibility or a rendering fix.
