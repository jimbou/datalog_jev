#!/bin/bash
# F2: every remaining pricer variant on the development subset (data/f2/dev_apps.txt, 92 of the 307 main apps), fixed
# before any result (2026-10-16): Sonnet 5.5 with the written definition, 3 samples, highest price (sonnet55def3, priced
# in the cloud session) and free combinations of existing prices:
#   tie-cs   Jev (choice-obj), ties broken by Sonnet 5 (sonnetp)     max-cs   max(Jev, Sonnet 5)
#   tie-cs55 Jev, ties broken by sonnet55def3                         max-cs55 max(Jev, sonnet55def3)
#   mean-cd  mean of the two Jev wordings (choice-obj, choice-def)
# Keys: main (rk) and GPT-only (gk) for all; K2 also for sonnet55def3 (Sonnet 5.5 is close to one of the main key's
# labelers). Baselines on the same apps: choice-obj, sonnetp (and choice-def on rk).
# Cores 12-15 at nice 10 only: cores 0-7 run the IzzyOnDroid build, cores 8-11 stay free for the user's other jobs.
set -e
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/f2/variants.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "F2V-START"
S55=data/jev_f2_dev_sonnet55def3_r0.jsonl
cp "$S55" data/jev_holes_android_fw_sonnet55def3_r0.jsonl
for spec in "tie choice-obj sonnetp tie-cs" "max choice-obj sonnetp max-cs" "tie choice-obj sonnet55def3 tie-cs55" \
            "max choice-obj sonnet55def3 max-cs55" "mean choice-obj choice-def mean-cd"; do
  $C python3 analysis/f2_combine.py $spec >> $L
done
run() {  # KEY TAG: evaluate on the main graphs (all apps), then keep the dev apps
  local k=$1 t=$2
  if [ ! -s data/android_fm-$k-${t}_f2all.jsonl ]; then
    OUT_SUFFIX=_f2all JOBS=4 $C python3 analysis/evaluate.py fm-$k-$t > data/f2/eval_${k}_$t.log 2>&1
  fi
  dev data/android_fm-$k-${t}_f2all.jsonl fm-$k-${t}_dev
  log "EVAL $k $t"
}
dev() {  # SRC NAME: rows of the dev apps -> data/android_NAME.jsonl
  python3 -c "
import json
dev = {l.strip() for l in open('data/f2/dev_apps.txt')}
with open('data/android_$2.jsonl', 'w') as f:
    for l in open('$1'):
        if json.loads(l)['app'] in dev: f.write(l)"
}
for t in sonnet55def3 tie-cs max-cs tie-cs55 max-cs55 mean-cd; do
  for k in rk gk; do run $k $t; done
done
run k2 sonnet55def3
for k in rk gk k2; do for t in choice-obj sonnetp; do dev data/android_fm-$k-$t.jsonl fm-$k-${t}_dev; done; done
R=data/f2/variants_results.txt
: > $R
for name in fm-rk-choice-obj fm-rk-sonnetp fm-rk-choice-def fm-rk-sonnet55def3 fm-rk-tie-cs fm-rk-max-cs fm-rk-tie-cs55 \
            fm-rk-max-cs55 fm-rk-mean-cd fm-gk-choice-obj fm-gk-sonnetp fm-gk-sonnet55def3 fm-gk-tie-cs fm-gk-max-cs \
            fm-gk-tie-cs55 fm-gk-max-cs55 fm-gk-mean-cd fm-k2-choice-obj fm-k2-sonnetp fm-k2-sonnet55def3; do
  for a in 0.05 0.1; do
    echo "== ${name}_dev alpha $a" >> $R
    $C python3 analysis/app_ltt.py ${name}_dev --alpha $a | tail -n 2 >> $R
  done
done
log "F2V-DONE"
