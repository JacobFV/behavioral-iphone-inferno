# First-release setup review after durable attempt85

Three concrete onboarding gaps remain. Existing successful local workflows are
real, but do not yet amount to a fresh-machine setup guide. No runtime, code or
frozen source was changed for this review.

1. **The runtime descriptor is the largest missing handoff.** APP_IMPORT lists
   its schema, but offers neither a complete annotated example nor an ordered
   explanation of where each required retained provenance artifact comes from.
   `prepare-import.py:51–106` requires not just firmware/tools: helper-build source
   pins, original cache-install profile/report/serial/readback, raw-ramdisk
   preparation, lineage evidence and an eligible stopped overlay report. A user
   with an IPSW, emulator and IPA still cannot supply these honestly. Even a user
   already holding all required artifacts must reverse-engineer the exact JSON
   to connect them. The actual runtime used here points to this machine's
   historical files. Highest-impact next documentation work: a complete
   placeholder-only runtime descriptor with a field-to-producing-command or
   retained-artifact table, clearly stating which initialized runtime lineage
   is prerequisite and not yet a fresh-setup product. Do not generate provenance
   assertions or present firmware availability alone as readiness.

2. **The generic app operator path is not connected to the three-command guide.**
   boot-import runs in the foreground; its help exposes no viewer endpoint.
   APP_IMPORT says operators may observe/control but does not link the concrete
   steps: use a second terminal, `NEW-INSTALLED/boot/command.json` for the private
   `-vnc unix:...` socket, `run observe`, then the separate serial `owned-control`
   path, and finally `control --report NEW-INSTALLED/boot finish-observation` only
   for the intended normal outcome. BOOT.md:147–155 and OWNED_JOURNEY.md:154–200
   already contain these pieces, but the latter mixes fixture-specific strict
   telemetry/coordinates with generic apps. A short generic operator section
   should connect those existing tools, warn that VNC pointer routing is not the
   demonstrated HID route, and avoid offering fixture OPEN or fixed coordinates
   as arbitrary-IPA controls. Run85 makes the outcome distinction practical:
   ACK0 was delivery=unproven, pixels stayed0, and forensic interruption retained
   failure rather than normal completion. No callback/freeze cause is established.

3. **Host prerequisites are split across pages and imprecise at the entry point.**
   RELEASE names ARM64 Linux; README:142–160 gives Ubuntu24.04 ARM64 dependencies
   and explains that the build root must be retained (binary is not standalone).
   The IPA guide links neither. `prepare-import.py` uses hashlib.file_digest,
   requiring Python3.11+, while the build paragraph says only Python3. The normal
   headless observer imports Pillow (`vnc-control.py:17`), documented only in
   BOOT.md. A concise prerequisite link/block should identify the tested platform,
   Python3.11+/Pillow for this CLI/viewer path, local tool/runtime inputs and
   retained build-root requirement. This is documentation alignment, not a claim
   of support for other Linux architectures or dependency versions.

CLI help for observe and owned-control was read successfully, without actions.
The durable source-clone problem has already been addressed and exercised through
host preparation and recovery staging; it should not be reopened with another
wrapper. Existing stage/boot gates must remain strict. Mac/Xcode is deferred and
is not a prerequisite for this prebuilt-IPA subset. `sources.json` records the
reviewed source identity; no general compatibility or release-readiness claim.
