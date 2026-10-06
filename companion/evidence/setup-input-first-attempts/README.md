# First live setup input observations

The actual boot11 framebuffer shows original iOS Hello setup, a status bar, home
indicator and information button. Root reviewed frame0017 and the included VNC
captures. This establishes visible setup UI, not completed setup or owned app
execution.

The private Unix VNC client sent one upward swipe and one information-button tap.
Its recorded pointer packets completed, but the captured frames did not show a
confirmed resulting navigation. Hello language animation alone is not input proof.
Touch routing is under investigation; do not label these as successful gestures.
No host window, clipboard, network listener, guest policy change or activation
operation was used. The guest remains live; these are input/capture records, not
stopped-disk hashes or final boot duration.

A second information tap held1second and observed3seconds after release. A second
swipe held0.5seconds, traversed20steps over3seconds, and observed10seconds after
release. Both completed wire delivery, with the same Hello setup UI and no
confirmed navigation. These results justify targeted input/MT-SPI tracing, not
a speculative coordinate or device-behavior change. Source8502618b01 adds bounded
optional gesture timing while retaining previous defaults.
