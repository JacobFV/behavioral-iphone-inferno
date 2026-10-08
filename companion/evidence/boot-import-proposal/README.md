# Minimal verified-stage → installed boot wrapper

Proposal only; no implementation, VM, disk hash pass or metadata action. This is
based on actual coordinated stage2 and installed run79, whose launch/report pins
are retained in `source-bindings.json`. Generic run79 displayed the imported
bundled text and counter0→1 according to root's separate visual review. This
proposal does not substitute that observation for a future wrapper execution.

## CLI and authority

```
companion/run boot-import --stage /external/STAGE/verified-stage.json \
  --stage-sha256 HEX --session /external/PREPARED/session.json \
  --output /external/NEW-BOOT --seconds 1200
```

First subset: accept only a successful coordinator layout, with no INCOMPLETE or
failure marker; fresh outside-Git output; explicit single VM; bounded seconds
(default1200, proposed1..3600). Stage hash binds the expected session SHA. No
profile/base/binary/argv overrides, arbitrary command execution, retries,
automatic taps, Home, OPEN, sample or CPU diagnostic. Existing installed launchd
job can attempt its configured app launch; host wrapper cannot assert it succeeded.

1. Strict bounded JSON and exact stage SHA; schema/eligible are merely an entry
   gate. Require report path STAGE/recovery-run/report.json and standard retention
   there, plus STAGE/content-check.json. Pin these bytes against the stage record.
2. `import_stage.validate_session(session, stage.session_sha256)` revalidates the
   IPA/import tree, sources, runtime/profile, cache provenance and original base.
3. `import_stage.verify_stopped(context, report, retention, checkpoint)` reruns
   actual raw readback/finish/QMP/process/FD/ancestry gates. Use its fresh result;
   compare stable report/retention/content/checkpoint/session bindings against the
   pinned stage, not volatile descriptor timestamps. Require remaining depth.
4. Derive installed profile from `runtime_record.inputs.profile`, *not*
   `session.recovery_profile`. Its original kernel/DT/trustcache/profile pins are
   already validated; boot.load_profile remains the original loader.
5. Hash source inventory before launch; bind exact fixed argv below, stage/session
   hashes and revalidated metadata in a new launch journal. Recheck source/metadata
   before process creation. Reuse the coordinator's readable-process single-VM
   guard and owned private-session cleanup; do not send commands to other VMs.
6. Normal boot's duration or an operator `finish-observation` ends the attempt.
   Preserve stdout/stderr, raw serial/control/QMP, report and stage/session/source
   linkage. Wrapper return0 means only normal runner completion. Missing input,
   interrupted/uncertain launch or cleanup becomes a retained failed/incomplete
   attempt, never app-success or new-stage eligibility. No automatic retry.

## Fixed argv mapping

Execute reviewed sibling `boot.py` with explicit flags derived from validated
fields, never `session.recovery_command` or JSON-supplied argv:

- `--profile`: runtime.inputs.profile.path
- `--binary` / `--manifest`: runtime.inputs.emulator / emulator_build paths
- `--overlay-tools-root`: runtime.overlay_tools_root
- `--overlay-base-report`: freshly reverified stage report (paired six auxiliaries
  are taken by existing overlay loader, no separate unbound auxiliary source)
- `--disk-boot --launchd-unsecure-cache --control-mailbox --guest-hid-serial`
- `--guest-errors --capture-interval 10 --seconds <bounded> --output NEW/report`

The launchd-cache option is the already exercised owned-job loading configuration;
this wrapper adds no trust/signature metadata or validation patch. No probe
journey is enabled for generic uninstrumented IPAs. No startup touch trace or
headless observer is necessary to the first contract. Those diagnostic choices
were present/different in actual79 and must not be presented as identical runs.
The existing headless UNIX VNC and sole mailbox support explicit operator review
and actions; no window is opened on the user's display.

## Host source policy: fail ambiguity

Session2's boot.py SHA starts8089c0bb; actual79 used86e625db after a reviewed host
change. The installed profile, emulator, stage and app match, but host sources do
not. Do not infer a compatibility exemption from these filenames or successful
run79. Smallest first implementation: require sibling boot/control source hashes
match session.sources, as stage-import does, and record all direct dependencies.
Execute the wrapper from a stable baseline worktree when consuming session2.
This avoids a new trusted-source-descriptor design in the first slice. A future
reviewed explicit host-runtime selection can decouple versioned preparer/runtime
without weakening provenance; it is not implicit permission in the current plan.
The session's pinned original source root is validated as evidence, never blindly
executed as an arbitrary recovery argv.

## Existing APIs and remaining work

- `import_stage.py:validate_session`, `verify_content`, `verify_stopped` already
  implement input/raw/stopped gates; no new guest marker grammar is needed.
- `app-import.py:external_output` supplies fresh outside-Git output checks.
- `stage-import.py:source_inventory`, `no_running_emulator`, `owned_group_members`,
  `stop_owned_group` provide reviewed host patterns; avoid copying weaker variants.
- `boot.py:load_profile/main` supplies fixed installed mode, direct root overlay,
  sole serial transport, no-input display and normal QMP cleanup.
- `disk_overlay.py:load_stopped_overlay/create_recorded_overlay` checks retained
  backing identities/chain and clones six auxiliaries. Current stage depth3 allows
  one installed depth4 layer. No automatic flattening, retirement or parent chmod.

No new firmware/helper/app artifact is required for the session2 example. Missing
required inputs are only the explicit pinned stage and session selected by the
operator and a compatible stable host source tree; absence/drift fails clearly.
First actual validation should use the already imported demo from this same stage,
with root-reviewed pixels and ordinary controls; no routine mock expansion.
Disk preservation/freezing remains the existing explicit postflight workflow in
this smallest proposal. A normal boot report alone is not an eligible next base.
