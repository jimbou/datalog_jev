#!/bin/bash
# Main results under the rubric key (both models under the written definition; K2 or unknown where they disagree).
# Waits for Sonnet's relabeling to cover every method.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/rk_chain.log; }
while [ "$(wc -l < data/oracle-rubric-sonnet5.jsonl)" -lt "$(wc -l < data/rubric_methods.tsv)" ] || pgrep -f "[r]un_oracle.py claude-sonnet-5 rubric" > /dev/null; do sleep 300; done
log "RK-START sonnet=$(wc -l < data/oracle-rubric-sonnet5.jsonl)"
export JOBS=5
FINE="0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5"
for p in choice-obj sonnetp b6 freq uniform q27 qflash dsflash gflash luna; do
  timeout 14400 python3 analysis/evaluate.py rk-$p > data/eval_rk-$p.log 2>&1
  d=""; case $p in b6) d="--deltas $FINE";; uniform) d="--deltas 0.5,1,2,3";; esac
  python3 analysis/app_ltt.py rk-$p --alpha 0.05 --eps 0.1 --splits 200 $d > data/ltt_rk-${p}_a05.log 2>&1
  python3 analysis/app_ltt.py rk-$p --alpha 0.1 --eps 0.1 --splits 200 $d > data/ltt_rk-${p}_a1.log 2>&1
  log "END rk-$p"
done
log RK-DONE
