# Behavioral iPhone on Inferno

This local fork builds on ChefKiss Inferno instead of reimplementing UIKit and
Foundation. Upstream history and notices are preserved. The initial upstream pin
is recorded in upstream.json; the remote is named `upstream`. This checkout has
not been published to a GitHub account.

The objective is a reproducible Linux runner for real iOS app execution, with
headless control, screenshots, repeatable journeys and measured resource use.
The older clean-room effort is preserved in ../behavioral-iphone. Its fixtures,
strict image comparisons and dashboard may be reused as integration tools; its
synthetic references are not native iOS acceptance evidence.

## Initial milestones

1. Build the actual upstream aarch64 system emulator with Apple-device support.
2. Execute the firmware-free QMP smoke and retain the binary/source identity.
3. Prepare an explicitly documented iOS image profile outside Git, then establish
   a real boot, display and input path. This has not been performed yet.
4. Install one owned, unencrypted application and execute an end-to-end journey.
5. Measure cold/warm launch, memory, CPU, reliability and parallel density before
   claiming cheap runner economics. Add the existing visualization dashboard only
   after real backend captures are available.

`python3 companion/smoke.py --binary PATH` starts `-machine none -accel tcg -S`
with no display, guest image or CPU, talks QMP, verifies that the executable lists
`t8030`, and shuts it down. It reports control-plane results only; it does not
claim iOS boot or app compatibility. Build instructions will be recorded with the
working build script and local evidence in PROGRESS.md.

## Source facts and limits

At the pinned source, t8030 defaults to 4 GiB guest RAM and an 828x1792 display.
It requires a device tree and kernel during initialization; unlike `none`, it
cannot be used for an image-free smoke. Its direct-kernel path invokes upstream
kernel patches, so future runs must not be called unmodified iOS. See
hw/arm/apple-silicon/t8030.c and hw/core/null-machine.c.

Inferno's iOS18.5 boot issue is marked done, but that is not a complete app or
Metal compatibility guarantee. Linux KVM support remains an open upstream issue.
No numerical throughput or cost claim has been verified in this fork.

- Source: https://github.com/ChefKissInc/Inferno
- KVM: https://github.com/ChefKissInc/Inferno/issues/87
- iOS18.5: https://github.com/ChefKissInc/Inferno/issues/241
- eShard UI work: https://www.eshard.com/blog/emulating-ios-14-with-qemu-part2

All original licenses remain in force. Companion additions are identified as
downstream AI-assisted work; the upstream README describes the upstream project.
