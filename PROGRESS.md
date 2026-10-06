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

## First executable checkpoint

Build succeeded at committed fork revision a63bb71bac. The pinned upstream base
is unchanged; the one upstream build change explicitly links liblzfse for the
Apple SoC code, whose boot.c already calls lzfse_decode_buffer. Its dependency
was previously supplied only by the optional DMG module. The minimal build also
needs explicit PNG support. No runtime behavior or Apple firmware was patched
by this companion work.

Root independently ran companion/smoke.py against the built binary. QMP greeting,
capability negotiation, version/machine/status/CPU queries and graceful shutdown
passed. The real executable advertises t8030; this none-machine run had zero guest
CPUs and no running guest. It establishes executable/control-plane operation,
not iOS boot, app launch, graphics compatibility or runner economics.

Committed evidence: companion/evidence/initial-build.json and
companion/evidence/initial-qmp-smoke.json. Their binary SHA256 values match.
Raw build output and stderr remain in .local-build/build.log and
.local-build/reports/initial-qmp-smoke/. Dependencies, the source checkout,
branding resources and binary are local and ignored by Git; retain the build
root together rather than distributing only the executable.

Next milestone: prepare a documented, authorized iOS image profile outside Git
and establish real boot/display/input, then run one owned app. No firmware was
downloaded and no native/simulator parity claim is made. Current bootstrap is
Ubuntu24.04 ARM64 only; other runner architectures need their own dependency lock.
