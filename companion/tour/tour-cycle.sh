#!/bin/bash
# tour-cycle.sh PLAN FIRST_BOOT_NUMBER [SKIP] : boot from the setup-complete base, tour, restart on freeze.
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}   # holds env.sh (see env.example.sh) and logs
source $WORK/env.sh; cd $R
PLAN=$1; n=$2; skip=${3:-0}; L=$WORK/cycle.log
BASE=${TOUR_BASE:-$A/fresh-boot-r6/boot/report.json}   # a normally stopped, preserved, setup-complete boot
total=$(python3 -c "import json;print(len(json.load(open(\"$PLAN\"))[\"apps\"]))")
sc(){ python3 -c "print(round($1/$2*32767))"; }
prev=-1; boots=0
while [ $skip -lt $total ] && [ $boots -lt 12 ]; do
  boots=$((boots+1))
  B=$A/tour-boot-$n
  echo "$(date +%T) boot $n skip=$skip" >> $L
  if [ "${ATTACH:-0}" = 1 ]; then ATTACH=0; SOCK=$(python3 -c "import json;a=json.load(open(\"$B/command.json\"));print([x for x in a if \"vnc.sock\" in str(x)][0][5:])")
  else
  nice -n 5 python3 companion/boot.py --profile $P --binary $R/.local-build/build/qemu-system-aarch64 --manifest $R/.local-build/build-manifest.json --overlay-tools-root $T --overlay-base-report $BASE --disk-boot --launchd-unsecure-cache --control-mailbox --guest-hid-serial --guest-errors --capture-interval 10 --seconds 21000 ${USB_SOCKET:+--usb-socket $USB_SOCKET} --output $B > $WORK/tour-boot-$n.log 2>&1 &
  until [ -f $B/command.json ]; do sleep 5; done
  until [ $(ls $B/frames 2>/dev/null | wc -l) -ge 66 ]; do sleep 10; done
  SOCK=$(python3 -c "import json;a=json.load(open(\"$B/command.json\"));print([x for x in a if \"vnc.sock\" in str(x)][0][5:])")
  nohup $TOUR/record.sh $B $B/rec >/dev/null 2>&1 &
  companion/run owned-control --report $B --output $B/op-unlock swipe $(sc 416 832) $(sc 1765 1792) $(sc 416 832) $(sc 500 1792) --duration-ms 1500 >/dev/null; sleep 60
  timeout 1000 python3 $TOUR/bringup.py $B >> $L 2>&1
  fi
  python3 companion/app-tour.py --report $B --socket $SOCK --plan $PLAN --output $B/tour-$skip-$(date +%s) --no-record --freeze-dir $B/rec --skip $skip > $WORK/tour-$n.log 2>&1
  rc=$?
  python3 companion/qmp_control.py --report $B finish-observation >/dev/null 2>&1
  touch $B/rec/STOP; wait
  if [ $rc = 3 ]; then f=$(python3 -c "import json;print([x for x in json.load(open(\"$(ls -d $B/tour-*/ | tail -1)actions.json\")) if \"frozen_after\" in x][-1][\"index\"])"); skip=$((f>skip ? f-1 : skip+1)); [ $skip -le $prev ] && skip=$((prev+1)); prev=$skip; echo "$(date +%T) boot $n froze after index $f -> resume at $skip" >> $L
  else echo "$(date +%T) boot $n completed rc=$rc" >> $L; break; fi
  n=$((n+1))
done
echo DONE >> $L
