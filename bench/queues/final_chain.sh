#!/bin/bash
# Final unattended chain: the Sonnet stated-confidence pricer on the main key and the K2 key, more seeds for it
# on the deletion benchmarks, the summaries, and one consolidated summary file.
cd "$HOME/receipts" || exit 1
export JOBS=6
log() { echo "$1 $(date +%F-%T)" >> data/final_chain.log; }
log FINAL-START

log "START sonnetp"
timeout 14400 python3 analysis/evaluate.py sonnetp > data/eval_sonnetp.log 2>&1
log "END sonnetp rc=$? records=$(wc -l < data/android_sonnetp.jsonl)"
python3 analysis/app_ltt.py sonnetp --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_sonnetp_a05.log 2>&1
python3 analysis/app_ltt.py sonnetp --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_sonnetp_a1.log 2>&1
python3 analysis/app_ltt.py sonnetp --alpha 0.05 --eps 0.1 --splits 200 --deltas 0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5 > data/ltt_sonnetp_fine_a05.log 2>&1
python3 analysis/app_ltt.py sonnetp --alpha 0.1 --eps 0.1 --splits 200 --deltas 0.001,0.002,0.003,0.004,0.005,0.0075,0.01,0.02,0.03,0.05,0.075,0.1,0.15,0.2,0.3,0.5 > data/ltt_sonnetp_fine_a1.log 2>&1
log "START k2-sonnetp"
timeout 14400 python3 analysis/evaluate.py k2-sonnetp > data/eval_k2-sonnetp.log 2>&1
log "END k2-sonnetp rc=$? records=$(wc -l < data/android_k2-sonnetp.jsonl)"
python3 analysis/app_ltt.py k2-sonnetp --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_k2-sonnetp_a05.log 2>&1
python3 analysis/app_ltt.py k2-sonnetp --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_k2-sonnetp_a1.log 2>&1
log "START k1c-0.1-1-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.1-1-sonnetp > data/eval_k1c-0.1-1-sonnetp.log 2>&1
log "END k1c-0.1-1-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.1-1-sonnetp.jsonl)"
log "START k1-0.1-1-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.1-1-sonnetp > data/eval_k1-0.1-1-sonnetp.log 2>&1
log "END k1-0.1-1-sonnetp rc=$? records=$(wc -l < data/android_k1-0.1-1-sonnetp.jsonl)"
log "START k1c-0.1-2-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.1-2-sonnetp > data/eval_k1c-0.1-2-sonnetp.log 2>&1
log "END k1c-0.1-2-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.1-2-sonnetp.jsonl)"
log "START k1-0.1-2-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.1-2-sonnetp > data/eval_k1-0.1-2-sonnetp.log 2>&1
log "END k1-0.1-2-sonnetp rc=$? records=$(wc -l < data/android_k1-0.1-2-sonnetp.jsonl)"
log "START k1c-0.1-3-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.1-3-sonnetp > data/eval_k1c-0.1-3-sonnetp.log 2>&1
log "END k1c-0.1-3-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.1-3-sonnetp.jsonl)"
log "START k1-0.1-3-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.1-3-sonnetp > data/eval_k1-0.1-3-sonnetp.log 2>&1
log "END k1-0.1-3-sonnetp rc=$? records=$(wc -l < data/android_k1-0.1-3-sonnetp.jsonl)"
log "START k1c-0.25-2-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.25-2-sonnetp > data/eval_k1c-0.25-2-sonnetp.log 2>&1
log "END k1c-0.25-2-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.25-2-sonnetp.jsonl)"
log "START k1c-0.5-2-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.5-2-sonnetp > data/eval_k1c-0.5-2-sonnetp.log 2>&1
log "END k1c-0.5-2-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.5-2-sonnetp.jsonl)"
log "START k1-0.25-2-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.25-2-sonnetp > data/eval_k1-0.25-2-sonnetp.log 2>&1
log "END k1-0.25-2-sonnetp rc=$? records=$(wc -l < data/android_k1-0.25-2-sonnetp.jsonl)"
log "START k1-0.5-2-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.5-2-sonnetp > data/eval_k1-0.5-2-sonnetp.log 2>&1
log "END k1-0.5-2-sonnetp rc=$? records=$(wc -l < data/android_k1-0.5-2-sonnetp.jsonl)"
log "START k1c-0.25-3-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.25-3-sonnetp > data/eval_k1c-0.25-3-sonnetp.log 2>&1
log "END k1c-0.25-3-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.25-3-sonnetp.jsonl)"
log "START k1c-0.5-3-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1c-0.5-3-sonnetp > data/eval_k1c-0.5-3-sonnetp.log 2>&1
log "END k1c-0.5-3-sonnetp rc=$? records=$(wc -l < data/android_k1c-0.5-3-sonnetp.jsonl)"
log "START k1-0.25-3-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.25-3-sonnetp > data/eval_k1-0.25-3-sonnetp.log 2>&1
log "END k1-0.25-3-sonnetp rc=$? records=$(wc -l < data/android_k1-0.25-3-sonnetp.jsonl)"
log "START k1-0.5-3-sonnetp"
timeout 7200 python3 analysis/evaluate.py k1-0.5-3-sonnetp > data/eval_k1-0.5-3-sonnetp.log 2>&1
log "END k1-0.5-3-sonnetp rc=$? records=$(wc -l < data/android_k1-0.5-3-sonnetp.jsonl)"
python3 analysis/k1_summary.py --alpha 0.1 > data/k1_summary_final_a10.log 2>&1
python3 analysis/k1_summary.py --alpha 0.05 > data/k1_summary_final_a05.log 2>&1
python3 analysis/k1_summary.py --class-level --alpha 0.1 > data/k1c_summary_final_a10.log 2>&1
python3 analysis/k1_summary.py --class-level --alpha 0.05 > data/k1c_summary_final_a05.log 2>&1
python3 analysis/b3_summary.py k2-b3 > data/b3_summary_k2.log 2>&1
log "SUMMARIES-DONE"
{ for f in data/ltt_au-choice-obj_a05.log data/ltt_au-choice-obj_a1.log data/ltt_sonnetp_a05.log data/ltt_sonnetp_a1.log data/ltt_sonnetp_fine_a05.log data/ltt_sonnetp_fine_a1.log data/ltt_k2-choice-obj_a05.log data/ltt_k2-choice-obj_a1.log data/ltt_k2-b6_fine_a05.log data/ltt_k2-b6_fine_a1.log data/ltt_k2-sonnetp_a05.log data/ltt_k2-sonnetp_a1.log data/b3_summary_k2.log data/k2_labels_all.log data/k1_summary_final_a10.log data/k1_summary_final_a05.log data/k1c_summary_final_a10.log data/k1c_summary_final_a05.log data/master.log data/final_chain.log; do echo "=================== $f"; tail -25 "$f" 2>/dev/null; done; } > data/FINAL_SUMMARY.txt 2>&1
log "FINAL-CHAIN-DONE"
