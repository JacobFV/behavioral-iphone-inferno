# Source-inventory preflight correction

Actual coordinated-stage-demo-1 failed before output creation or VM launch because
its source snapshot included nonexistent `companion/profile.py`. The previous
read-only helper replay did not call `main()`'s source inventory and missed this
integration error. Root retained that failure as `dd7f284ca9`; its log and failed
launch remain untouched.

`3acefa0d91` factors the actual inventory into `source_inventory()`, called by
`main()` before session validation. It hashes real coordinator/validator files
and direct runner imports. The profile loader is `boot.py:load_profile`, not a
separate module. A direct import of the fixed coordinator followed by
`paths, hashes = module.source_inventory()` passed for all ten files. The check
also imported `boot.load_profile`, asserted its code filename is the inventoried
`boot.py`, and compared boot/control hashes against the original session2 pins.
`actual-preflight.json` records the resulting exact source hashes. Compilation
also passed. No disk hashing, output directory creation, VM or retry was performed.

The stable worktree runner/control remains the session2 baseline; the newer root
pending-branch runner was not substituted into this prepared session.
