# Actual durable host source check

The retained commands created a NEW persistent detached local clone, with no
network protocol, submodule initialization, hardlinks or object alternates.
`validation.json` records exact argv, raw output hashes, commit, clean status,
object link counts and Python source hashes. `helper-source-check.json` compares
the four source pins of the retained helper60 build against this clone. The three
help logs prove CLI routing only. No preparation, disk validation, staging or VM
was performed; existing sessions and frozen source trees were untouched.

Persistent artifact: `/home/brandonin/.local/share/inferno/host-runtimes/ipa-release-host-1`.
The clone is intentionally retained there, not included in Git. The source
revision is explicit; it is not an assertion that every later runner revision is
compatible. Source pin and runtime validators remain mandatory. This ordinary
Git workflow supersedes the earlier new-command suggestion in
`../release-host-pin-proposal/`; no new pinning wrapper was implemented.
