#!/bin/bash
# interact.sh APP SESSION_DIR : a few real touches inside an imported app while try-app.sh records,
# so the footage shows the app responding, not just its first screen. APP is the app's base name
# (MF-/L- prefixes and -rN suffixes are stripped). Coordinates are in the 832x1792 capture panel,
# measured from recorded frames of each app.
set -u
cd "$(dirname "$0")/../.."
APP=$(echo "$1" | sed -E 's/^(MF|L|C)-//; s/-r[0-9a-z]+$//; s/-ent$//'); B=$2
sc(){ python3 -c "print(round($1/$2*32767))"; }
c(){ companion/run owned-control --report $B --output $B/act-$(date +%s%N) "$@" >/dev/null 2>&1; }
tap(){ c tap $(sc $1 832) $(sc $2 1792) --duration-ms 120; sleep ${3:-8}; }
swipe(){ c swipe $(sc $1 832) $(sc $2 1792) $(sc $3 832) $(sc $4 1792) --duration-ms ${5:-500}; sleep ${6:-6}; }
back(){ tap 70 125 ${1:-8}; }
case $APP in
  HelloSwiftUI|HelloSPM) tap 300 332 12; back; tap 300 420 12; back; tap 300 508 15; back ;;
  HelloStoryboard) for i in 1 2 3; do tap 416 644 6; done ;;
  HelloAsync) tap 260 212 20; tap 260 212 20 ;;
  HelloMixed) for i in 1 2 3 4; do tap 416 1024 5; done ;;
  Puzzles) tap 600 280 25; swipe 416 1200 416 600; back 10; tap 600 710 25; back 10; tap 600 1150 25 ;;
  Reader) tap 416 896 20; swipe 700 900 130 900; swipe 700 900 130 900 ;;
  ACEDrawingViewDemo|JotDemo)
    swipe 150 500 650 700 900 4; swipe 650 500 150 900 900 4; swipe 200 1100 640 1100 900 4
    swipe 416 400 416 1300 900 4; swipe 150 1300 650 1400 900 6 ;;
  Tipulator) tap 416 1300 6; tap 250 1300 6; tap 580 1450 6; swipe 416 1000 416 500 ;;
  swift-2048) tap 416 900 20
    for d in "416 1300 416 600" "700 900 130 900" "416 600 416 1300" "130 900 700 900"; do set -- $d; swipe $1 $2 $3 $4 300 10; done ;;
  SwiftUI2048)
    for d in "416 1300 416 600" "700 900 130 900" "416 600 416 1300" "130 900 700 900" "416 1300 416 600" "700 900 130 900"; do
      set -- $d; swipe $1 $2 $3 $4 300 8; done ;;
  NetNewsWire|Clendar|SwiftUIKit) tap 416 600 15; back 10; swipe 416 1300 416 500; tap 416 900 15 ;;
  *) # Generic exploration for apps without a measured script (the OSS corpus): open the first
     # thing near the top, scroll, go back, open something lower down, then a sideways swipe.
     tap 416 420 12; swipe 416 1300 416 600 800 6; back 8; tap 416 900 12; swipe 700 900 130 900 500 6
     echo "interact.sh: generic touches for $APP" ;;
esac
echo "interacted $APP"
