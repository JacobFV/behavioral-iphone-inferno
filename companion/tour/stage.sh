#!/bin/bash
# stage.sh NAME SCRIPT EXTRA... : run one coordinator stage with COMMON+HB args, log, wait
source ~/inferno-chain/env.sh; cd $R
name=$1; script=$2; shift 2
nice -n 5 python3 companion/$script $COMMON $HB "$@" --output $A/$name > ~/inferno-chain/$name.log 2>&1
echo "rc=$?" >> ~/inferno-chain/$name.log
