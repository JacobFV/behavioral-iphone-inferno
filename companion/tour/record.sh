#!/bin/bash
# record.sh BOOTDIR OUTDIR : chained 120 s no-input observers at 1 Hz until OUTDIR/STOP exists
B=$1; O=$2; mkdir -p $O
SOCK=$(python3 -c "import json;a=json.load(open(\"$B/command.json\"));print([x for x in a if \"vnc.sock\" in str(x)][0][5:])")
cd ~/Documents/behavioral-iphone-inferno
n=0; while [ ! -e $O/STOP ] && [ -S $SOCK ]; do companion/run observe --socket $SOCK --output $O/chunk-$(printf %04d $n) --observe-seconds 120 >/dev/null 2>&1; n=$((n+1)); done
