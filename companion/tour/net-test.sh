#!/bin/bash
# net-test.sh NAME IPA [SECONDS] : boot an imported app (default: the NetworkProbe app) with the USB
# companion attached, switch the phone to CDC-NCM, start the userspace NCM bridge in the companion,
# and record what happens: the guest's INFERNO_NET_* serial lines, bridge frame counts, a ping and
# a DNS lookup from the companion, and the app's screen (contact sheet via try-app.sh).
#   Needs: a running usb-companion (USB_SOCKET, its guest-key and SSH port), RUNTIME pinning a
#   helper build whose launch wrapper contains NetHelper.h (any build after 10d73d6).
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
NAME=${1:-NetProbe}; IPA=${2:-$A/net-probe-build/NetworkProbe.ipa}; SECS=${3:-1200}
USBDIR=${USBDIR:-$HOME/.local/share/inferno/usb/net1}
export USB_SOCKET=${USB_SOCKET:-$USBDIR/usb.sock}
SSHC="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -i $USBDIR/guest-key -p ${USB_SSH_PORT:-22330} inferno@127.0.0.1"
L=$WORK/net-$NAME.log; : > $L
log(){ echo "$(date +%T) $*" | tee -a $L; }
$TOUR/try-app.sh $NAME $IPA $SECS >> $L 2>&1 &
TRY=$!
until grep -q READY $WORK/session-$NAME.log 2>/dev/null; do sleep 15; kill -0 $TRY 2>/dev/null || { log "try-app exited early"; exit 1; }; done
B=$A/session-$NAME
log "session ready: $B"
# The bracket keeps pkill from matching this very ssh command line (which would kill the shell).
$SSHC 'sudo pkill -f "[n]cm-bridge"; sudo python3 ncm-mode.py get; sudo python3 ncm-mode.py set 3; sleep 15; sudo python3 ncm-mode.py configs; sudo systemctl stop usbmuxd.service usbmuxd.socket 2>/dev/null; sudo pkill -x usbmuxd; for t in 1 2 3; do sudo python3 ncm-mode.py select 5 && break; sleep 5; done; sudo python3 ncm-mode.py get' >> $L 2>&1
# (usbmuxd in the companion claims the usbmux interface, and set_configuration then fails with EBUSY)
grep -q "active config now 5" $L || { log "NCM configuration 5 not reached; see the ncm-mode output above"; }
log "mode switched; starting bridge"
$SSHC 'sudo nohup python3 ncm-bridge.py > bridge.log 2>&1 &' >> $L 2>&1
for i in $(seq 1 40); do
  sleep 15
  grep -a -E "INFERNO_NET_" $B/serial.log | tail -2 | sed 's/^/  serial: /' >> $L
  $SSHC 'tail -1 bridge.log; ping -c1 -W2 192.168.77.2 >/dev/null && echo PING-OK || echo ping-fail' >> $L 2>&1
  grep -q PING-OK $L && break
done
$SSHC 'cat bridge.log | head -20; ip -br addr show ncm0; sudo tail -20 /var/log/inferno-ncm-dnsmasq.log; ping -c3 192.168.77.2' >> $L 2>&1
log "network checks done; app keeps recording until try-app finishes"
wait $TRY
log "DONE $NAME"
