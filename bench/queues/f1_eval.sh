#!/bin/bash
# F1: main evaluation (fm-rk-choice-obj: FlowDroid's models, rubric key, Jev prices) on the rescued apps, separately for
# the retry graphs (data/graphs_f1) and the step-e fallback graphs (data/graphs_f1e_fb). Sonnet prices come later.
cd ~/receipts
L=~/receipts/data/f1/f1_eval.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "EVAL-START"
for d in f1 f1e_fb; do
  GRAPHS_DIR=data/graphs_$d OUT_SUFFIX=_$d JOBS=4 taskset -c 8-15 python3 analysis/evaluate.py fm-rk-choice-obj > data/f1/eval_$d.log 2>&1
  log "EVAL-$d rc=$? apps=$(wc -l < data/android_fm-rk-choice-obj_$d.jsonl)"
done
log "EVAL-DONE"
