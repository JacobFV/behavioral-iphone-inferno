#!/bin/bash
# crash-lane.sh : re-run apps that crashed at start and keep their full crash text (the serial
# console carries each new CrashReporter .ips between INFERNO_APP_CRASH_BEGIN/END). Runs beside other
# lanes (INFERNO_ALLOW_CONCURRENT=1) on the pinned emulator. Output: $WORK/crash-triage/NAME.txt
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
export RUNTIME=$A/runtime-r7/runtime.json INFERNO_ALLOW_CONCURRENT=1
O=$WORK/crash-triage; mkdir -p $O; Q=$O/lane.log
W=~/.local/share/inferno/swift-ipas
grab(){ awk '/INFERNO_APP_CRASH_BEGIN/{p=1} p{print} /INFERNO_APP_CRASH_END/{p=0}' "$1" > "$2"; }
for spec in "T-Velik $W/prepared-corpus/Velik.ipa" "T-CompositionalDiffable $W/prepared-corpus/CompositionalDiffable.ipa" \
            "T-Sol $W/prepared-corpus/Sol.ipa" "T-SwiftUIKit $W/prepared/L-SwiftUIKit.ipa" "T-NetNewsWire-ent $W/prepared-mf/NetNewsWire-ent.ipa"; do
  read n ipa <<< "$spec"
  [ -f "$ipa" ] || ipa=$(ls $W/*/$(basename $ipa) 2>/dev/null | head -1)
  rm -rf $A/$n-prep $A/$n-stage $A/session-$n
  $TOUR/try-app.sh $n $ipa 150 > /dev/null 2>&1
  grab $A/session-$n/serial.log $O/$n.txt; cp $A/session-$n/serial.log $O/$n.serial.log 2>/dev/null
  echo "$(date +%T) $n: $(tail -1 $WORK/try-$n.log | cut -c1-100); crash blocks $(grep -c INFERNO_APP_CRASH_BEGIN $O/$n.txt)" >> $Q
  rm -f $A/session-$n/disks/*.qcow2 $A/$n-prep/*.qcow2 2>/dev/null
done
# Built-in Maps and Stocks: one session, open each from Home.
n=T-MapsStocks
if $TOUR/session.sh $n > /dev/null 2>&1; then
  B=$A/session-$n; SOCK=$(python3 -c "import json;a=json.load(open('$B/command.json'));print([x for x in a if 'vnc.sock' in str(x)][0][5:])")
  python3 companion/app-tour.py --report $B --socket $SOCK --plan $TOUR/plan-maps-stocks.json --output $B/tour --no-record > $O/$n.tour.log 2>&1
  python3 companion/qmp_control.py --report $B finish-observation >/dev/null 2>&1; touch $B/rec/STOP
  grab $B/serial.log $O/$n.txt; cp $B/serial.log $O/$n.serial.log
  echo "$(date +%T) $n: crash blocks $(grep -c INFERNO_APP_CRASH_BEGIN $O/$n.txt)" >> $Q
else echo "$(date +%T) $n BOOT-FAILED" >> $Q; fi
echo CRASH-LANE-DONE >> $Q
