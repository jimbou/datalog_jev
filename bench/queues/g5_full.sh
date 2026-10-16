#!/bin/bash
# G5 + G1 rerun on all 307 main apps, after the F2 dev choice (data/f2/variants_results.txt, 2026-10-16):
# 1. Sonnet 5.5 with the definition, 3 samples (sonnet55def3: cloud prices, dev subset + rest of the main corpus) and the
#    dev subset's best variant max-cs55 = max(Jev choice-obj, sonnet55def3), keys rk, gk and k2.
# 2. G1 again with analysis/g1_fact.py fixed: methods without a GPT label were priced 0.5 by evaluate.py (a flow at
#    0.5); now 0 in gptfact and 1 in gptfactu.
# LTT on all apps at alpha 0.05 and 0.1 for the new runs and the baselines choice-obj and sonnetp.
# Waits for the IzzyOnDroid dataset step (f3_dataset.sh rewrites data/holes_android_fw.jsonl). Cores 12-15, nice 10.
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/g5_full.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "G5-WAIT"
until grep -qE "F3D-PUSHED|PUSH-FAILED|F3D-ABORT" data/f3/f3_dataset.log 2>/dev/null && ! pgrep -f "[f]3_dataset.sh" > /dev/null; do
  sleep 120
done
log "G5-START"
cat data/jev_f2_dev_sonnet55def3_r0.jsonl data/jev_f2_rest_sonnet55def3_r0.jsonl > data/jev_holes_android_fw_sonnet55def3_r0.jsonl
$C python3 analysis/f2_combine.py max choice-obj sonnet55def3 max-cs55 >> $L
for t in sonnet55def3 max-cs55; do
  for k in rk gk k2; do
    OUT_SUFFIX= JOBS=4 $C python3 analysis/evaluate.py fm-$k-$t > data/eval_fm-$k-$t.log 2>&1
    log "EVAL $k $t rc=$?"
  done
done
$C python3 analysis/g1_fact.py prices >> $L
for t in gptfact gptfactu; do
  OUT_SUFFIX= JOBS=4 $C python3 analysis/evaluate.py fm-rk-$t > data/eval_fm-rk-$t.log 2>&1
  log "EVAL rk $t rc=$?"
done
$C python3 analysis/g1_fact.py summary fm-rk-jevfact fm-rk-gptfact fm-rk-gptfactu >> $L
R=data/g5_full_results.txt
: > $R
for name in fm-rk-choice-obj fm-rk-sonnetp fm-rk-sonnet55def3 fm-rk-max-cs55 fm-gk-choice-obj fm-gk-sonnetp \
            fm-gk-sonnet55def3 fm-gk-max-cs55 fm-k2-choice-obj fm-k2-sonnetp fm-k2-sonnet55def3 fm-k2-max-cs55; do
  for a in 0.05 0.1; do
    echo "== $name alpha $a" >> $R
    $C python3 analysis/app_ltt.py $name --alpha $a | tail -n 2 >> $R
  done
done
log "G5-DONE"
