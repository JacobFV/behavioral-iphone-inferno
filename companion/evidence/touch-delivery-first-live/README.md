# Actual live touch delivery boundary

Boot12 uses trace-only emulator58436578 and progressed stopped11 state. Initial
and live QMP query-mice report current absolute Apple Multitouch HID SPI. Root
reviewed setupframe0005, then enabled all nine exact input/MT trace events only
for two bounded windows. Every enable/disable and input request is retained.

VNC information-button tap held1second; original input events and MT host callback
recorded expected coordinates, then21queued reports including make/touch/break/out.
Direct QMP tap at identical normalized coordinates recorded the same MT callback
and3queued make/break/out reports. No dequeue/control/transmit-drain trace occurred
in either window. Captures show setup without confirmed navigation. All events
were disabled afterward; root exclusively owned input.

This proves host routing and report queueing. It establishes no completed traced
packet consumption during these windows, not necessarily zero partial SPI bytes.
Coordinates, button and device selection are not the demonstrated failure.
Read-only source inspection found correct original-DT IRQ wiring; next observation
is whether the guest armed its interrupt and completed firmware initialization.
No device behavior or guest security policy has been changed for this diagnosis.

This is a live evidence snapshot, not stopped disk hashes/final boot duration.
Neither UIKit execution nor touch response is claimed.
