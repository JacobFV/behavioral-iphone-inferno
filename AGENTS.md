# Inferno companion work rules

This is the user-requested pivot from ../behavioral-iphone, not a continuation of
its framework-reimplementation backlog. Read companion/README.md, PROGRESS.md and NEXT_SESSION.md.
Preserve upstream history, license notices and attribution. Keep our integration
under companion/ where possible, with small reviewable upstream changes only when
an actual execution failure requires them.

- Keep working across status questions; answer briefly and resume active work.
  Only stop for a requested handoff/pause or a genuinely missing required input.
- Prefer integrated build/boot/app journeys over routine unit-test proliferation.
  This is a permanent user preference. Record source revisions and actual logs;
  do not treat an implementer's JSON assertion as execution evidence.
- A firmware-free QMP smoke is not an iOS boot, app launch, screenshot or benchmark.
  Distinguish those milestones explicitly. Fail missing requirements clearly.
- Use isolated clones/worktrees for parallel ownership and commit as work proceeds.
- Never open windows on the user's display. Use headless display/QMP or isolated
  virtual displays. Bind any remote display/control endpoints to local interfaces.
- Keep dependencies, build products, firmware, disks and credentials outside Git.
  Do not copy Apple implementation binaries into the tracked tree. Do not decrypt
  FairPlay, extract device keys, forge Apple signatures or impersonate iCloud.
- No automatic return to the archived implementation; reuse its app fixtures,
  automation and dashboard only where the new backend actually supports them.
