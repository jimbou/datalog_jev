#!/bin/bash
# Track EVAL: audited-key run, Sonnet stated-confidence pricer, then everything under the K2 key.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/master.log; }
log EVAL-START
while pgrep -f "[o]vernight6.sh" > /dev/null; do sleep 60; done
export JOBS=3

log "START au-choice-obj"
timeout 14400 python3 analysis/evaluate.py au-choice-obj > data/eval_au-choice-obj.log 2>&1
log "END au-choice-obj rc=$? records=$(wc -l < data/android_au-choice-obj.jsonl)"
python3 analysis/app_ltt.py au-choice-obj --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_au-choice-obj_a05.log 2>&1
python3 analysis/app_ltt.py au-choice-obj --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_au-choice-obj_a1.log 2>&1
for i in $(seq 1 120); do if grep -q " priced " data/sonnetp.log 2>/dev/null; then break; fi; sleep 120; done
N=$(wc -l < data/jev_holes_android_fw_sonnetp_r0.jsonl 2>/dev/null || echo 0)
log "SONNETP-PRICES methods=$N"
if [ "${N:-0}" -ge 17000 ]; then
  log "START sonnetp"
  timeout 14400 python3 analysis/evaluate.py sonnetp > data/eval_sonnetp.log 2>&1
  log "END sonnetp rc=$? records=$(wc -l < data/android_sonnetp.jsonl)"
  python3 analysis/app_ltt.py sonnetp --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_sonnetp_a05.log 2>&1
  python3 analysis/app_ltt.py sonnetp --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_sonnetp_a1.log 2>&1
  python3 analysis/app_ltt.py sonnetp --alpha 0.05 --eps 0.1 --splits 200 --deltas 0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5 > data/ltt_sonnetp_fine_a05.log 2>&1
  python3 analysis/app_ltt.py sonnetp --alpha 0.1 --eps 0.1 --splits 200 --deltas 0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5 > data/ltt_sonnetp_fine_a1.log 2>&1
  log "START k1-0.25-1-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1-0.25-1-sonnetp > data/eval_k1-0.25-1-sonnetp.log 2>&1
  log "END k1-0.25-1-sonnetp rc=$? records=$(wc -l < data/android_k1-0.25-1-sonnetp.jsonl)"
  log "START k1-0.5-1-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1-0.5-1-sonnetp > data/eval_k1-0.5-1-sonnetp.log 2>&1
  log "END k1-0.5-1-sonnetp rc=$? records=$(wc -l < data/android_k1-0.5-1-sonnetp.jsonl)"
  log "START k1c-0.25-1-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1c-0.25-1-sonnetp > data/eval_k1c-0.25-1-sonnetp.log 2>&1
  log "END k1c-0.25-1-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.25-1-sonnetp.jsonl)"
  log "START k1c-0.5-1-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1c-0.5-1-sonnetp > data/eval_k1c-0.5-1-sonnetp.log 2>&1
  log "END k1c-0.5-1-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.5-1-sonnetp.jsonl)"
  log "START k1c-0.75-1-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1c-0.75-1-sonnetp > data/eval_k1c-0.75-1-sonnetp.log 2>&1
  log "END k1c-0.75-1-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.75-1-sonnetp.jsonl)"
  log "START k1c-0.75-2-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1c-0.75-2-sonnetp > data/eval_k1c-0.75-2-sonnetp.log 2>&1
  log "END k1c-0.75-2-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.75-2-sonnetp.jsonl)"
  log "START k1c-0.75-3-sonnetp"
  timeout 7200 python3 analysis/evaluate.py k1c-0.75-3-sonnetp > data/eval_k1c-0.75-3-sonnetp.log 2>&1
  log "END k1c-0.75-3-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.75-3-sonnetp.jsonl)"
fi
python3 analysis/k1_summary.py --alpha 0.1 > data/k1_summary_final_a10.log 2>&1
python3 analysis/k1_summary.py --alpha 0.05 > data/k1_summary_final_a05.log 2>&1
python3 analysis/k1_summary.py --class-level --alpha 0.1 > data/k1c_summary_final_a10.log 2>&1
python3 analysis/k1_summary.py --class-level --alpha 0.05 > data/k1c_summary_final_a05.log 2>&1
log "EVAL-STAGE1-DONE"
while ! grep -q K2X-DONE data/k2_progress.log 2>/dev/null; do sleep 120; done
log "K2-KEY-START"
export JOBS=6

log "START k2-choice-obj"
timeout 14400 python3 analysis/evaluate.py k2-choice-obj > data/eval_k2-choice-obj.log 2>&1
log "END k2-choice-obj rc=$? records=$(wc -l < data/android_k2-choice-obj.jsonl)"
log "START k2-b6"
timeout 14400 python3 analysis/evaluate.py k2-b6 > data/eval_k2-b6.log 2>&1
log "END k2-b6 rc=$? records=$(wc -l < data/android_k2-b6.jsonl)"
log "START k2-b3"
timeout 14400 python3 analysis/evaluate.py k2-b3 > data/eval_k2-b3.log 2>&1
log "END k2-b3 rc=$? records=$(wc -l < data/android_k2-b3.jsonl)"
log "START k2-sonnetp"
timeout 14400 python3 analysis/evaluate.py k2-sonnetp > data/eval_k2-sonnetp.log 2>&1
log "END k2-sonnetp rc=$? records=$(wc -l < data/android_k2-sonnetp.jsonl)"
log "START k2-uniform"
timeout 10800 python3 analysis/evaluate.py k2-uniform > data/eval_k2-uniform.log 2>&1
log "END k2-uniform rc=$? records=$(wc -l < data/android_k2-uniform.jsonl)"
python3 analysis/app_ltt.py k2-choice-obj --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_k2-choice-obj_a05.log 2>&1
python3 analysis/app_ltt.py k2-choice-obj --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_k2-choice-obj_a1.log 2>&1
python3 analysis/app_ltt.py k2-b6 --alpha 0.05 --eps 0.1 --splits 200 --deltas 0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5 > data/ltt_k2-b6_fine_a05.log 2>&1
python3 analysis/app_ltt.py k2-b6 --alpha 0.1 --eps 0.1 --splits 200 --deltas 0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5 > data/ltt_k2-b6_fine_a1.log 2>&1
python3 analysis/app_ltt.py k2-sonnetp --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_k2-sonnetp_a05.log 2>&1
python3 analysis/app_ltt.py k2-sonnetp --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_k2-sonnetp_a1.log 2>&1
python3 analysis/b3_summary.py k2-b3 > data/b3_summary_k2.log 2>&1
python3 probes/k2_labels.py > data/k2_for_facts.log 2>&1
log "MASTER-DONE"
