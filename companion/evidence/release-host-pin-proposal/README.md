# One release usability improvement: retain the host source tree explicitly

Proposal only. No clone, source relocation, new session, disk hash or VM action.

## Observed gap

The IPA sequence now works, but its host source selection remains an operator
prerequisite hidden behind “use its reviewed stable host tree” in APP_IMPORT.md.
Actual session2 records its source root through
`/tmp/inferno-prepare-import/companion/boot.py`. `import_stage.validate_session`
resolves all66 source pins relative to that path and loads the pinned
prepare-import validator there. `stage-import.fixed_command` and
`boot-import.fixed_command` separately require exact sibling boot/control hashes.
Actual coordinator2 and wrapper81 therefore used specifically retained isolated
baseline trees rather than arbitrary current checkout code. A temporary directory
cleanup or editing that baseline breaks revalidation even if every firmware,
imported app and disk remains unchanged. A current checkout can also fail with
“Sibling runner/control differs from prepared session”. This is intentional
validation, but there is no operator command to establish durable source retention.

## Proposed single bounded deliverable

```
companion/run pin-import-host --revision COMMIT \
  --output ~/.local/share/inferno/host-runtimes/NEW-NAME
```

Create a NEW independent local Git clone from the selected already-present
committed revision, detached at that commit. Use no network, no submodules, no
hardlinked object dependency, no checkout of uncommitted files and no update of
an existing destination. Retain upstream history/license notices. Reject a
temporary destination in this first subset; never chmod or relocate an existing
host tree. Keep the command source-only: copy no firmware, disk, credentials,
build products or untracked content, and execute no imported application or VM.

The output contains a small host-selection manifest outside the cloned Git tree:
source repository/revision, destination, original command/tool identity, resolved
HEAD and a bounded inventory/hash of required companion source files. Pin the
entry points and direct dependencies already used by the pipeline. Keep any
metadata/journal outside that checkout so a clean committed source check remains
meaningful. Include an explicit retention marker and print the persistent
`source/companion/run` command path for prepare, stage and boot. Do not run these
steps automatically. Hashes describe the copied source, not runtime success.

Future preparations run FROM that clone. Existing prepare-import naturally
records its durable absolute source root, and the subsequent wrappers naturally
find matching siblings. No session schema/source-root override, validation waiver
or existing report rewrite is needed. In particular, this does NOT repair or
relocate session2; its historical required trees stay retained unchanged.

A real Git clone is useful here: prepare-import and build-import-launcher both
call `git rev-parse HEAD` for provenance. A plain file archive would require extra
builder changes or fabricated Git metadata. The clone also remains usable if the
original worktree is later removed. This proposal accepts the source/history
storage cost rather than silently retaining a dependency on the original .git.

## Small validation and limits

Validate with one actual local clone of a reviewed revision, compare its declared
source hashes and HEAD, then perform the existing host-only demo prepare from
that persistent path. Confirm the NEW session source root points into the
persistent clone, helper-source pins still match and every HFS readback passes.
Do not boot merely to test cloning. Existing failed/coordinator/wrapper evidence
stays unchanged. No extra routine test suite is needed.

This closes one concrete reproducibility gap. It does not package firmware/tools,
prove general IPA support, make old source versions interchangeable, eliminate
overlay retention requirements or solve the display freeze. The runtime descriptor
still explicitly binds the user-supplied original assets and reviewed cache/base
lineage; those checks must remain intact.
