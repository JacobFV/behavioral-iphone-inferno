#!/bin/bash
# rerun-lane.sh DIR NAME... : prepare each IPA in DIR, import it onto the setup-complete base, run it
# with its touch script, and keep its crash text (INFERNO_APP_CRASH blocks) and serial log.
# Runs beside other lanes. Output: $WORK/crash-triage/R-NAME.txt and lane-r5.log
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
export RUNTIME=$A/runtime-r7/runtime.json INFERNO_ALLOW_CONCURRENT=1 INTERACT=1
D=$1; shift; O=$WORK/crash-triage; mkdir -p $O; Q=$O/lane-r5.log
P=~/.local/share/inferno/swift-ipas/prepared-r5; mkdir -p $P
grab(){ awk '/INFERNO_APP_CRASH_BEGIN/{p=1} p{print} /INFERNO_APP_CRASH_END/{p=0}' "$1" > "$2"; }
for n in "$@"; do
  s=R5-$n
  python3 companion/tour/prepare-swift-ipa.py $D/$n.ipa $P/$n.ipa --ldid $N/ldid/ldid > $O/$s.prep.log 2>&1 || { echo "$(date +%T) $s PREPARE-IPA FAILED: $(tail -1 $O/$s.prep.log)" >> $Q; continue; }
  rm -rf $A/$s-prep $A/$s-stage $A/session-$s
  $TOUR/try-app.sh $s $P/$n.ipa 200 > /dev/null 2>&1
  grab $A/session-$s/serial.log $O/$s.txt; gzip -c $A/session-$s/serial.log > $O/$s.serial.log.gz 2>/dev/null
  echo "$(date +%T) $s: $(tail -1 $WORK/try-$s.log | cut -c1-120); crash blocks $(grep -c INFERNO_APP_CRASH_BEGIN $O/$s.txt)" >> $Q
  rm -f $A/session-$s/disks/*.qcow2 $A/$s-prep/*.qcow2 2>/dev/null
done
echo RERUN-LANE-DONE >> $Q
