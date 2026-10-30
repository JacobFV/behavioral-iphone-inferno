#!/bin/bash
# builtin-crash.sh NAME PLAN : capture crash text for built-in apps. The crash printer lives in the
# per-import launch wrapper, so this imports a harmless app (HelloSwiftUI) to get it, then tours PLAN.
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
export RUNTIME=$A/runtime-r7/runtime.json INFERNO_ALLOW_CONCURRENT=1
NAME=$1; PLAN=$2; O=$WORK/crash-triage; mkdir -p $O
rm -rf $A/$NAME-prep $A/$NAME-stage $A/session-$NAME
$TOUR/try-app.sh $NAME ~/.local/share/inferno/swift-ipas/prepared/L-HelloSwiftUI.ipa 900 > /dev/null 2>&1 &
until grep -q -E "READY|BOOT-FAILED" $WORK/session-$NAME.log 2>/dev/null; do sleep 15; done
B=$A/session-$NAME; SOCK=$(grep READY $WORK/session-$NAME.log | sed 's/.*vnc=//' | tail -1)
python3 companion/app-tour.py --report $B --socket $SOCK --plan $PLAN --output $B/tour --no-record > $O/$NAME.tour.log 2>&1
wait
awk '/INFERNO_APP_CRASH_BEGIN/{p=1} p{print} /INFERNO_APP_CRASH_END/{p=0}' $B/serial.log > $O/$NAME.txt
gzip -c $B/serial.log > $O/$NAME.serial.log.gz
echo "$(date +%T) $NAME: crash blocks $(grep -c INFERNO_APP_CRASH_BEGIN $O/$NAME.txt)" >> $O/lane.log
rm -f $B/disks/*.qcow2 $A/$NAME-prep/*.qcow2
