#!/bin/bash
# Runs on the emulation host; paths come from ~/inferno-chain/env.sh (see env.example.sh).
# chain-all.sh SUFFIX : whole fresh chain from initial volumes with current sources
set -u
X=$1
source ~/inferno-chain/env.sh; cd $R
L=~/inferno-chain; LOG=$L/chain-$X.log
run(){ name=$1; shift; echo "== $name $(date +%T)" >> $LOG; nice -n 5 python3 "$@" > $L/$name.log 2>&1; rc=$?; echo "rc=$rc" >> $L/$name.log; echo "   $name rc=$rc $(date +%T)" >> $LOG; [ $rc = 0 ] || exit $rc; }
CR=$I/initial-volumes-source-r2/copy.json
run iv-$X companion/stage-initial-volumes.py $COMMON $HB --root-copy-record $CR --root-copy-record-sha256 $(s $CR) --output $A/iv-$X
J=$A/iv-$X/initial-volumes.json
run seed-$X companion/stage-seed-data.py $COMMON $HB --initial-stage $J --initial-stage-sha256 $(s $J) --output $A/seed-$X
J=$A/seed-$X/seeded-data.json
run verify-$X companion/stage-verify-data.py $COMMON $HB --seed-stage $J --seed-stage-sha256 $(s $J) --output $A/verify-$X
J=$A/verify-$X/data-verified.json
run flatd-$X companion/flatten-verified-data.py --data-verified $J --data-verified-sha256 $(s $J) --overlay-tools-root $T --output $A/flatd-$X
J=$A/flatd-$X/flattened-data.json; G=$N/reproducible-grow-build-r2/build.json
run grow-$X companion/stage-grow-data.py $COMMON --helper-build $G --helper-build-sha256 $(s $G) --flattened-data $J --flattened-data-sha256 $(s $J) --output $A/grow-$X
J=$A/grow-$X/grown-data.json; SP=$N/sep-original.im4p; SR=$N/sep-original.json
run kb-$X companion/stage-sep-keybag.py $COMMON $HB --grown-stage $J --grown-stage-sha256 $(s $J) --sep-payload $SP --sep-payload-sha256 $(s $SP) --sep-record $SR --sep-record-sha256 $(s $SR) --output $A/kb-$X
KB=$A/kb-$X/sep-keybag.json
run flatk-$X companion/flatten-keybag.py --keybag-stage $KB --keybag-stage-sha256 $(s $KB) --overlay-tools-root $T --output $A/flatk-$X
FK=$A/flatk-$X/flattened-keybag.json; IB=$N/runtime-inspector-build-r2/build.json
run insp-$X companion/runtime-inspector/stage.py $COMMON --helper-build $IB --helper-build-sha256 $(s $IB) --keybag-stage $KB --keybag-stage-sha256 $(s $KB) --output $A/insp-$X
IN=$A/insp-$X/runtime-inspection.json; CB=$N/reproducible-cache-build-r2/build.json; C=~/.local/share/inferno/cachework
OC=$C/original-dyld_shared_cache_arm64e; PC=$C/patched/dyld_shared_cache_arm64e; SC=$PC.InfernoOriginalBytes
run cache-$X companion/stage-cache-patch.py --flattened-keybag $FK --flattened-keybag-sha256 $(s $FK) --inspection $IN --inspection-sha256 $(s $IN) --helper-build $CB --helper-build-sha256 $(s $CB) --original-cache $OC --original-cache-sha256 $(s $OC) --patched-cache $PC --patched-cache-sha256 $(s $PC) --sidecar $SC --sidecar-sha256 $(s $SC) --overlay-tools-root $T --output $A/cache-$X
D=$A/ipa-demo-r2; RB=$N/runtime-helpers-r3/build.json; PB=$N/reproducible-helper-build-r2/build.json
mkdir -p $A/ain-$X; python3 - "$IN" "$KB" "$RB" "$PB" "$D/imported/manifest.json" "$D/launcher/build-evidence.json" > $A/ain-$X/input.json <<P
import hashlib,json,sys
k=["inspection","keybag_stage","runtime_build","prepare_build","app_manifest","launcher_build"]
h=lambda p:hashlib.sha256(open(p,"rb").read()).hexdigest()
print(json.dumps({"schema":"inferno.fresh-runtime-artifact-input.v1","inputs":{n:{"path":p,"sha256":h(p)} for n,p in zip(k,sys.argv[1:])},"policy":"disable-five-unsupported-services"},indent=2))
P
AI=$A/ain-$X/input.json
run art-$X companion/prepare-fresh-runtime.py --input $AI --input-sha256 $(s $AI) --output $A/art-$X
RC=$A/cache-$X/renderer-cache.json; AR=$A/art-$X/fresh-runtime-artifacts.json
run fresh-$X companion/stage-fresh-runtime.py --renderer-stage $RC --renderer-stage-sha256 $(s $RC) --artifacts $AR --artifacts-sha256 $(s $AR) --overlay-tools-root $T --output $A/fresh-$X
echo DONE >> $LOG
