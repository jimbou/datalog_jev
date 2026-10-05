#!/bin/bash
# Budgeted verification (paper RQ "which assumptions to check"): rank receipt facts without labels, let the answer key
# verify the top K, recompute receipts and recertify. Main key: unlock policy at several budgets plus three other policies
# at K=100; K2 key: unlock at 50 and 200.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/verify_chain.log; }
export JOBS=3
log VERIFY-START
python3 analysis/verify_select.py choice-obj --policy unlock > data/verify_select_unlock.log 2>&1
for p in value count random; do python3 analysis/verify_select.py choice-obj --policy $p --budgets 100 > data/verify_select_$p.log 2>&1; done
run() {  # pricing unused verify-file
  VERIFY_FILE=data/verify/$3.json OUT_SUFFIX=_v$3 timeout 21600 python3 analysis/evaluate.py $1 > data/eval_$1_v$3.log 2>&1
  log "END $1 $3 rc=$? records=$(wc -l < data/android_$1_v$3.jsonl)"
  python3 analysis/app_ltt.py $1_v$3 --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_$1_v$3_a05.log 2>&1
  python3 analysis/app_ltt.py $1_v$3 --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_$1_v$3_a1.log 2>&1
}
for v in unlock_10 unlock_25 unlock_50 unlock_100 unlock_200 unlock_400 value_100 count_100 random_100; do run choice-obj choice-obj $v; done 2>/dev/null
log MAIN-DONE
for v in unlock_50 unlock_200; do run k2-choice-obj k2-choice-obj $v; done 2>/dev/null
log VERIFY-DONE
