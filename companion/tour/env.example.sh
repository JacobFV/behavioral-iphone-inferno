# Copy to $INFERNO_TOUR_WORK/env.sh (default ~/inferno-chain/env.sh) and adjust.
R=~/Documents/behavioral-iphone-inferno
I=~/.local/share/inferno/images/ios14b5
N=~/.local/share/inferno/native-probe
A=~/.local/share/inferno/app-import
T=~/.local/share/inferno/disk-overlay-tools
s(){ sha256sum "$1" | cut -d" " -f1; }
P=$I/profile/profile.json
