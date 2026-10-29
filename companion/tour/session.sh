#!/bin/bash
# session.sh N : boot once from the setup-complete base, unlock, dismiss alerts, and leave it
# running for interactive work (VNC socket printed). Stop with
#   python3 companion/qmp_control.py --report $A/session-N finish-observation
# Optional: USB_SOCKET=/path/usb.sock (a running usb-companion) attaches the USB transport.
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
n=$1; B=$A/session-$n
BASE=${TOUR_BASE:-$A/fresh-boot-r6/boot/report.json}
sc(){ python3 -c "print(round($1/$2*32767))"; }
nice -n 5 python3 companion/boot.py --profile $P --binary $R/.local-build/build/qemu-system-aarch64 --manifest $R/.local-build/build-manifest.json --overlay-tools-root $T --overlay-base-report $BASE --disk-boot --launchd-unsecure-cache --control-mailbox --guest-hid-serial --guest-errors --capture-interval 10 --seconds ${SECONDS_LIMIT:-21000} ${USB_SOCKET:+--usb-socket $USB_SOCKET} --output $B > $WORK/session-$n.log 2>&1 &
until [ -f $B/command.json ]; do sleep 5; done
until [ $(ls $B/frames 2>/dev/null | wc -l) -ge 66 ]; do sleep 10; done
SOCK=$(python3 -c "import json;a=json.load(open(\"$B/command.json\"));print([x for x in a if \"vnc.sock\" in str(x)][0][5:])")
nohup $TOUR/record.sh $B $B/rec >/dev/null 2>&1 &
companion/run owned-control --report $B --output $B/op-unlock swipe $(sc 416 832) $(sc 1765 1792) $(sc 416 832) $(sc 500 1792) --duration-ms 1500 >/dev/null; sleep 60
timeout 1000 python3 $TOUR/bringup.py $B >> $WORK/session-$n.log 2>&1
echo "READY report=$B vnc=$SOCK" | tee -a $WORK/session-$n.log
