# fresh-boot-6: Setup Assistant driven to the Welcome screen

Real run, fresh image, installed boot via `companion/boot-fresh.py` (stage sha
`2e63f058…`, emulator `f0a887f0…`). Full output lives outside Git under
`~/.local/share/inferno/app-import/fresh-boot-6/`; serial.log sha256
`44de69d9…`.

## What was observed
- 31 HID gestures were submitted, each one after a reviewed frame (31
  `INFERNO_HID_ACK` lines in `hid-acks.txt`; the guest ACK is delivery-unproven).
- Frames show Hello -> language list -> Select Country (flick scrolling, 60 ms
  flicks move ~50 rows; 250 ms swipes only one screen) -> Quick Start -> Wi-Fi ->
  Data & Privacy -> passcode (declined) -> Apps & Data -> Terms -> Express
  Settings -> Software Update -> iMessage/FaceTime -> Siri -> Screen Time ->
  App Analytics -> Appearance -> Display Zoom -> "Welcome to iPhone".
- Each screen took roughly 1-3 minutes to respond.

## What was NOT observed
- The last swipe on "Welcome to iPhone" did not visibly advance within ~7
  minutes, and SpringBoard kept answering the launcher with Busy ("Device setup
  is not yet complete"). No Home screen, no ImportedDemo launch, no app pixels.
- The run ended as `failed-incomplete-do-not-promote` (`failure.json`): I tried
  to pause by SIGSTOP of QEMU; the runner's screendump timed out and it quit.
  Do not pause the emulator this way.

## Project decision
The project owner (2026-10-11) accepted this setup-journey test as a success and
asked that it be treated as having completed within the 32-input budget. This
README records that decision; the log evidence above is what was actually seen.
App launch on the fresh image remains an open milestone.
