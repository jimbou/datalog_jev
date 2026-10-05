#!/bin/bash
# Evaluate the pricer panel and the wording ablation. Waits for the entry-restricted rebuild and for the pricing.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/panel_eval.log; }
while ! grep -q ENTRY-DONE data/entry_chain.log 2>/dev/null; do sleep 60; done
while ! grep -q PRICE-DONE data/panel_price.log 2>/dev/null; do sleep 60; done
export JOBS=6
log EVAL-START
FINE="0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5"
# phase 1: main key
for t in q27 luna gflash dsflash qflash taint choice; do
  log "START $t"
  timeout 14400 python3 analysis/evaluate.py $t > data/eval_$t.log 2>&1
  log "END $t rc=$? records=$(wc -l < data/android_$t.jsonl)"
  python3 analysis/app_ltt.py $t --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_${t}_a05.log 2>&1
  python3 analysis/app_ltt.py $t --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_${t}_a1.log 2>&1
  python3 analysis/app_ltt.py $t --alpha 0.05 --eps 0.1 --splits 200 --deltas $FINE > data/ltt_${t}_fine_a05.log 2>&1
  python3 analysis/app_ltt.py $t --alpha 0.1 --eps 0.1 --splits 200 --deltas $FINE > data/ltt_${t}_fine_a1.log 2>&1
done
log "PHASE1-DONE"
# phase 2: whole-class deletion at 50% and 75%, three seeds
for t in q27 luna gflash dsflash qflash; do
  for r in 0.5 0.75; do
    for s in 1 2 3; do
      timeout 7200 python3 analysis/evaluate.py k1c-$r-$s-$t > data/eval_k1c-$r-$s-$t.log 2>&1
    done
  done
  log "DELETION $t done"
done
python3 analysis/k1_summary.py --class-level --alpha 0.1 > data/k1c_summary_panel_a10.log 2>&1
python3 analysis/k1_summary.py --class-level --alpha 0.05 > data/k1c_summary_panel_a05.log 2>&1
log "PHASE2-DONE"
# phase 3: the code-derived key
for t in q27 luna gflash dsflash qflash; do
  timeout 14400 python3 analysis/evaluate.py k2-$t > data/eval_k2-$t.log 2>&1
  log "END k2-$t rc=$?"
  python3 analysis/app_ltt.py k2-$t --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_k2-${t}_a05.log 2>&1
  python3 analysis/app_ltt.py k2-$t --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_k2-${t}_a1.log 2>&1
done
log "PANEL-EVAL-DONE"
