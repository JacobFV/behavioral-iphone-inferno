#!/bin/bash
# exp-freeze.sh LANE : one lane of the freeze A/B (companion/FREEZE_EXPERIMENT_1.md).
# Pops trials ("ID ARM" lines) from $EXP/trials.txt under a lock until it is empty. Each trial
# boots once from the setup-complete base with that arm's knobs, unlocks, clears alerts, then
# runs the fixed 23-app plan from index 0 with freeze detection, and appends one JSON line to
# $EXP/results.jsonl. Arms share one experiment binary so the knob is the only difference.
set -u
TOUR=$(cd "$(dirname "$0")" && pwd)
WORK=${INFERNO_TOUR_WORK:-$HOME/inferno-chain}
source $WORK/env.sh; cd $R
EXP=${EXP:-$WORK/exp1}; LANE=$1
PLAN=${EXP_PLAN:-$TOUR/plan-builtin-pass1.json}
export INFERNO_ALLOW_CONCURRENT=1
export QEMU_BIN=$R/.local-build/build-exp/qemu-system-aarch64 QEMU_MANIFEST=$R/.local-build/build-exp-manifest.json
pop(){ ( flock 9; t=$(head -1 $EXP/trials.txt); [ -n "$t" ] && sed -i 1d $EXP/trials.txt; echo "$t" ) 9>$EXP/.lock; }
while t=$(pop); [ -n "$t" ]; do
  read id arm <<< "$t"
  case $arm in
    base)   export BOOT_EXTRA="" BOOT_TIMEOUT=1500 ;;
    delay)  export BOOT_EXTRA="--qemu-global apple-display-pipe-v4.completion-delay-ns=16666667" BOOT_TIMEOUT=1500 ;;
    single) export BOOT_EXTRA="--tcg-thread single" BOOT_TIMEOUT=3600 ;;
    *) echo "unknown arm $arm" >&2; continue ;;
  esac
  n=X-$id-$arm; B=$A/session-$n; t0=$(date +%s)
  echo "$(date +%T) lane $LANE start $n" >> $EXP/lanes.log
  if ! $TOUR/session.sh $n > /dev/null 2>&1; then
    echo "{\"id\":$id,\"arm\":\"$arm\",\"lane\":$LANE,\"outcome\":\"boot-failed\",\"seconds\":$(( $(date +%s)-t0 ))}" >> $EXP/results.jsonl
    python3 companion/qmp_control.py --report $B finish-observation >/dev/null 2>&1; touch $B/rec/STOP 2>/dev/null
    for _ in $(seq 60); do pgrep -f "output $B( |$)" >/dev/null || break; sleep 5; done
    continue
  fi
  SOCK=$(python3 -c "import json;a=json.load(open('$B/command.json'));print([x for x in a if 'vnc.sock' in str(x)][0][5:])")
  t1=$(date +%s)
  python3 companion/app-tour.py --report $B --socket $SOCK --plan $PLAN --output $B/exp-tour --no-record --freeze-dir $B/rec > $EXP/tour-$n.log 2>&1
  rc=$?
  python3 companion/qmp_control.py --report $B finish-observation >/dev/null 2>&1
  touch $B/rec/STOP
  python3 - "$B" "$id" "$arm" "$LANE" "$rc" "$t0" "$t1" >> $EXP/results.jsonl <<'PY'
import json, sys, time
b, i, arm, lane, rc, t0, t1 = sys.argv[1:]
try:
    log = json.load(open(b + '/exp-tour/actions.json'))
except Exception:
    log = []
done = sum(1 for x in log if 'app_end' in x)
frz = [x for x in log if 'frozen_after' in x]
print(json.dumps({'id': int(i), 'arm': arm, 'lane': int(lane), 'rc': int(rc),
                  'outcome': 'frozen' if frz else ('completed' if int(rc) == 0 else 'error'),
                  'apps_done': done, 'frozen_after_index': frz[0]['index'] if frz else None,
                  'tour_seconds': round(time.time() - float(t1)), 'seconds': round(time.time() - float(t0)),
                  'session': b}))
PY
  # Let this lane's emulator exit before the next trial so lanes never overlap themselves.
  for _ in $(seq 60); do pgrep -f "output $B( |$)" >/dev/null || break; sleep 5; done
  echo "$(date +%T) lane $LANE done $n rc=$rc" >> $EXP/lanes.log
done
echo "$(date +%T) lane $LANE EMPTY" >> $EXP/lanes.log
