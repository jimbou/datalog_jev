#!/bin/bash
# Budgeted checking (RQ5) and TaintBench (RQ6) under the rubric key. Runs alongside rk_chain.sh (needs only rk-choice-obj).
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/rk_verify_chain.log; }
while ! grep -q "END rk-choice-obj" data/rk_chain.log 2>/dev/null; do sleep 300; done
log RKV-START
python3 analysis/verify_select.py rk-choice-obj --policy count --budgets 25,100,400 --tag rk_ > data/verify_select_rk_count.log 2>&1
python3 analysis/verify_select.py rk-choice-obj --policy unlock --budgets 25,100 --tag rk_ > data/verify_select_rk_unlock.log 2>&1
python3 analysis/verify_select.py rk-choice-obj --policy random --budgets 100 --tag rk_ > data/verify_select_rk_random.log 2>&1
export JOBS=3
for v in rk_count_25 rk_count_100 rk_count_400 rk_unlock_25 rk_unlock_100 rk_random_100; do
  VERIFY_FILE=data/verify/$v.json OUT_SUFFIX=_v$v timeout 21600 python3 analysis/evaluate.py rk-choice-obj > data/eval_rk-choice-obj_v$v.log 2>&1
  log "END verify $v"
done
python3 analysis/verify_summary.py rk-choice-obj rk-choice-obj_vrk_count_25 rk-choice-obj_vrk_count_100 rk-choice-obj_vrk_count_400 \
  rk-choice-obj_vrk_unlock_25 rk-choice-obj_vrk_unlock_100 rk-choice-obj_vrk_random_100 > data/verify_summary_rk.log 2>&1
log "RKV-VERIFY-DONE"
for p in choice-obj sonnetp; do
  GRAPHS_DIR=data/graphs_tbl OUT_SUFFIX=_tbl timeout 3600 python3 analysis/evaluate.py rk-$p > data/eval_rk-${p}_tbl.log 2>&1
done
log RKV-DONE
