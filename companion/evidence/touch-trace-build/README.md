# Touch delivery observation build

Sourcea51980a836 built successfully with simulated SEP and KVM preserved. It adds
six disabled-by-default MT-SPI tracepoints without changing device behavior, plus
the companion-only private single-owner QMP mailbox. The actual executable lists
all six MT-SPI events and input_event_btn/abs/sync. QMP control-plane check passed;
this is not touch-delivery proof.

Boot11 actual Hello UI and failed fast/slow gestures motivate the observation.
Nextboot12 preserves stopped11 root and all paired auxiliary state. Root owns the
bounded trace/input window; do not add a second QMP client. Guest SPI drains prove
bus reads, not UIKit acceptance; success still requires visible input response.
