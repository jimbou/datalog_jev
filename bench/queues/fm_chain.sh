#!/bin/bash
# Fix 1 (REVIEW_FIXES.md): holes only where FlowDroid has no model (prefix fm-), under the main (rubric) key.
# Waits for rk_paper_chain.sh. Then: main results for five pricers, budgeted checking, TaintBench.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/fm_chain.log; }
while pgrep -f "[q]ueues/rk_paper_chain.sh" > /dev/null; do sleep 300; done
log FM-START
export JOBS=6
FINE="0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5"
for p in choice-obj sonnetp b6 freq uniform; do
  timeout 14400 python3 analysis/evaluate.py fm-rk-$p > data/eval_fm-rk-$p.log 2>&1
  d=""; case $p in b6) d="--deltas $FINE";; uniform) d="--deltas 0.5,1,2,3";; esac
  for a in 0.02 0.05 0.1; do
    python3 analysis/app_ltt.py fm-rk-$p --alpha $a --eps 0.1 --splits 200 $d > data/ltt_fm-rk-${p}_a$a.log 2>&1
  done
  log "END fm-rk-$p"
done
python3 analysis/sensitivity.py fm-rk-choice-obj --alpha 0.05 --splits 200 > data/sensitivity_fm.log 2>&1
python3 analysis/conformal.py fm-rk-choice-obj > data/conformal_fm.log 2>&1
log "FM-MAIN-DONE"
# budgeted checking under fm (facts ranked from the fm receipts)
python3 analysis/verify_select.py fm-rk-choice-obj --policy unlock --budgets 25,100 --tag fm_ > data/verify_select_fm_unlock.log 2>&1
python3 analysis/verify_select.py fm-rk-choice-obj --policy count --budgets 100 --tag fm_ > data/verify_select_fm_count.log 2>&1
python3 analysis/verify_select.py fm-rk-choice-obj --policy random --budgets 100 --tag fm_ > data/verify_select_fm_random.log 2>&1
export JOBS=4
for v in fm_unlock_25 fm_unlock_100 fm_count_100 fm_random_100; do
  VERIFY_FILE=data/verify/$v.json OUT_SUFFIX=_v$v timeout 21600 python3 analysis/evaluate.py fm-rk-choice-obj > data/eval_fm-rk-choice-obj_v$v.log 2>&1
  log "END verify $v"
done
python3 analysis/verify_summary.py fm-rk-choice-obj fm-rk-choice-obj_vfm_unlock_25 fm-rk-choice-obj_vfm_unlock_100 \
  fm-rk-choice-obj_vfm_count_100 fm-rk-choice-obj_vfm_random_100 > data/verify_summary_fm.log 2>&1
# TaintBench under fm
for p in choice-obj sonnetp uniform; do
  GRAPHS_DIR=data/graphs_tbl OUT_SUFFIX=_tbl timeout 3600 python3 analysis/evaluate.py fm-rk-$p > data/eval_fm-rk-${p}_tbl.log 2>&1
done
log FM-DONE
