# Reviewed command preparation only

The exact pinned command in plan.json is prepared for NEW initial-volumes-stage-1.
No VM was launched by this task. Production90 owns the slot until root confirms
stop and authorizes the next run. Execution source remains unchanged in
/tmp/inferno-initial-volumes at976afb970f; documentation was edited separately.

All explicit profile/extraction/copy/helper/probe/tool/emulator record pins were
checked, current immutable-copy identity matches the prior full-hash preflight,
and the CLI help/source inventory was inspected. No second8GiB hash pass was
performed. The coordinator will rerun ordinary input verification itself when
explicitly launched. An actual recovery result is still required; no initial
volume or initialized-runtime success follows from this command preparation.
