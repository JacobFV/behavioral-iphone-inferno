#!/bin/sh
# Run inside the USB companion (root) after ncm-mode.py: give the iPhone's CDC-NCM link an
# address, serve it DHCP + DNS, and NAT it out through the companion's own uplink.
#   net-up.sh [IFACE]   (default: the first interface bound to cdc_ncm)
set -eu
IF=${1:-$(for i in /sys/class/net/*; do [ "$(basename "$(readlink -f "$i/device/driver" 2>/dev/null)")" = cdc_ncm ] && basename "$i"; done | head -1)}
[ -n "$IF" ] || { echo "no cdc_ncm interface"; exit 1; }
UP=$(ip route show default | awk '{print $5; exit}')
ip link set "$IF" up
ip addr replace 192.168.77.1/24 dev "$IF"
sysctl -q -w net.ipv4.ip_forward=1
iptables -t nat -C POSTROUTING -s 192.168.77.0/24 -o "$UP" -j MASQUERADE 2>/dev/null ||
  iptables -t nat -A POSTROUTING -s 192.168.77.0/24 -o "$UP" -j MASQUERADE
pkill -f "dnsmasq.*inferno-ncm" 2>/dev/null || true
dnsmasq --conf-file=/dev/null --pid-file=/run/inferno-ncm-dnsmasq.pid --interface="$IF" --bind-interfaces \
  --dhcp-range=192.168.77.10,192.168.77.50,12h --dhcp-option=3,192.168.77.1 --dhcp-option=6,192.168.77.1 \
  --log-dhcp --log-facility=/var/log/inferno-ncm-dnsmasq.log --server=8.8.8.8 --server=1.1.1.1 \
  --dhcp-leasefile=/var/lib/misc/inferno-ncm.leases --dhcp-authoritative
echo "NCM up: $IF 192.168.77.1/24, uplink $UP, DHCP 192.168.77.10-50"
