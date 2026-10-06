# Touch reset-boundary observation build

Source9f92661b1b builds emulatorfda9447b41d7bd170a0abf6b56f4b0db822ff9ca84add3e648299d2aa7f59505.
The existing disabled-by-default boot-command trace gains phase and buffer-length
metadata at firstbyte, completion, bootresponsequeue and interruptackconsumption.
No device behavior changes. Actual boot13 showed only a reset firstbyte plus
inactive SPI/GPIO snapshots even after reviewed Hello; this trace distinguishes
partial reset from a queued response awaiting acknowledgment. Original driver
can clock four zero bytes during initial poweroffconfiguration, so that reset
alone is not evidence firmware boot started. Exact inspection is retained nearby.

Build and firmware-free control-plane checks passed. Next real guest execution
and bounded original IORegistry snapshot are still required.
