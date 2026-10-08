# Flatten a verified fresh keybag preparation

`keybag_state.py` validates the typed, normally stopped `sep-keybag.json` result, original serial checkpoint and sole finish, reviewed preparation inputs, original API outcomes, frozen seven-file namespace, and grown predecessor. Its `source_pins()` returns the validator and transitive producer source hashes; `validate(path, sha256, pins, tools_root)` is read-only and returns the manifest, validated chain/tool, Path-valued preparation inputs, and identities. Consumers must preserve and recheck their source snapshot across validation and subsequent work.

`flatten-keybag.py` accepts this result with `--keybag-stage` and `--keybag-stage-sha256`, pinned `--overlay-tools-root`, and an exclusively new external `--output`. It creates no VM. It requires the actual 32 GiB, three-layer stopped root and at least **34 GiB free**, even if sparse conversion would allocate less. A storage shortage is a failure before output creation, not permission to remove retained evidence.

The pinned qemu-img converts the root to raw and compares logical bytes. The tool verifies both GPT copies, complete raw and source hashes, source identities, all paired references, and source/tool pins. It fsyncs and freezes only the new raw, then publishes `flattened-keybag.json` and a KEEP marker. Original roots and six auxiliary files are never chmodded or copied over. Every future consumer must retain the exact six stopped auxiliary references; replacing them with blanks would discard initialized state.

The output is `flattened-fresh-keybag-not-runtime-ready`, with `ipa_runtime_ready:false`. It preserves successful original keybag API initialization; it does not independently verify destination SEP bytes, whole Data after growth, or installed runtime behavior. No key material is printed or included in tracked evidence. The inspector's later observation-only descendant cannot replace this input.

Actual execution requires a reviewed input and adequate storage. Source checks and read-only schema validation do not establish a completed conversion; inspect actual convert/compare logs and the final result.
