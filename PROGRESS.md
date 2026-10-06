# Inferno companion execution record

## 2026-10-05: user-directed pivot

The user requested wrapping ../behavioral-iphone and creating this companion fork.
Upstream cc4302a99167abec69b714cfd00c38caece7e7de is checked out with complete
commit ancestry (partial clone fetches historical blobs on demand), remote upstream,
and local branch companion/linux-runner. No GitHub-hosted fork was created.

The prior effort's source, pending branches, tracked patches and selected evidence
are preserved there; ../behavioral-iphone-handoff.bundle backs up its Git refs.
Its framework workers and demo server were stopped. The prior project remains
unfinished; no phase-completion claim accompanies the pivot.

Current host reports aarch64 Linux. glib2.80 and pixman0.42 are available; several
build dependencies and Meson/Ninja were absent. Local dependency/bootstrap build
work is underway. No firmware has been downloaded, no iOS boot performed and no
application run on this backend yet.
