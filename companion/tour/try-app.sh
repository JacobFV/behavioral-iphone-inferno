#!/bin/bash
# try-app.sh NAME IPA [WATCH_SECONDS] : import an IPA onto the setup-complete base, boot it once,
# unlock (its launcher opens the app), record the display for WATCH_SECONDS, stop normally, and
# write a contact sheet. One emulator at a time; run several NAMEs sequentially.
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
NAME=$1; IPA=$2; WATCH=${3:-180}
export BRINGUP_NO_HOME=1  # keep the launched app in the foreground while recording
# Imports onto the base land on Home page 2 after "Imported Demo": row 3, column 4.
export BRINGUP_ICON=${BRINGUP_ICON:-700,644}
RT=${RUNTIME:-$A/runtime-r6/runtime.json}
L=$WORK/try-$NAME.log; : > $L
python3 companion/prepare-import.py --ipa $IPA --runtime $RT --runtime-sha256 $(s $RT) --output $A/$NAME-prep >> $L 2>&1 || { echo "PREPARE FAILED" | tee -a $L; exit 1; }
S=$A/$NAME-prep/session.json
nice -n 5 python3 companion/stage-import.py --session $S --session-sha256 $(s $S) --output $A/$NAME-stage >> $L 2>&1 || { echo "STAGE FAILED" | tee -a $L; exit 1; }
TOUR_BASE=$A/$NAME-stage/recovery-run/report.json $TOUR/session.sh $NAME >> $L 2>&1 &
B=$A/session-$NAME
until grep -q READY $WORK/session-$NAME.log 2>/dev/null; do sleep 15; done
sleep $WATCH
grep -a -E "INFERNO_LAUNCHER_V1 event=open-callback" $B/serial.log | tail -3 >> $L
python3 companion/qmp_control.py --report $B finish-observation >> $L 2>&1
touch $B/rec/STOP; wait
python3 - "$B" "$WORK/sheet-$NAME.png" <<'P'
import sys, glob
from PIL import Image
fs = sorted(glob.glob(sys.argv[1] + '/rec/chunk-*/observed-*.png'))[-12:]
ims = [Image.open(f).convert('RGB') for f in fs]
for im in ims: im.thumbnail((260, 560))
W = Image.new('RGB', (6 * 270, 2 * 570), 'white')
for i, im in enumerate(ims): W.paste(im, ((i % 6) * 270, (i // 6) * 570))
W.save(sys.argv[2]); print('sheet', sys.argv[2], len(fs))
P
echo "DONE $NAME" | tee -a $L
