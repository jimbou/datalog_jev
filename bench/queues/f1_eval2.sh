#!/bin/bash
# F1: after the Sonnet prices (sonnetp) finish, fill failed methods once, then evaluate the other main pricers on the
# rescued apps (retry graphs data/graphs_f1, step-e fallback graphs data/graphs_f1e_fb).
cd ~/receipts
L=~/receipts/data/f1/f1_eval.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
while pgrep -f "run_sonnet_price.py claude-sonnet-5" > /dev/null; do sleep 120; done
(cd probes && BACKEND=claude PRICE_THREADS=4 python3 run_sonnet_price.py claude-sonnet-5 sonnetp holes_android_fw >> ../data/f1/price_sonnetp_f1.log 2>&1)
log "SONNETP-DONE $(wc -l < data/jev_holes_android_fw_sonnetp_r0.jsonl)"
for p in sonnetp b6 freq uniform; do
  for d in f1 f1e_fb; do
    GRAPHS_DIR=data/graphs_$d OUT_SUFFIX=_$d JOBS=4 taskset -c 8-15 python3 analysis/evaluate.py fm-rk-$p > data/f1/eval_${p}_$d.log 2>&1
    log "EVAL-$p-$d rc=$? rows=$(wc -l < data/android_fm-rk-${p}_$d.jsonl)"
  done
done
log "EVAL2-DONE"
