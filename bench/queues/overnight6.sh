#!/bin/bash
# Trimmed heavy class-level deletion: 75% for 3 seeds, 90% for seed 1 only (a 90% run takes about 70 minutes).
cd "$HOME/receipts" || exit 1
export JOBS=3
while pgrep -f "[e]valuate.py k1c-0.9-1-choice-obj" > /dev/null; do sleep 30; done
echo "QUEUE6-START $(date +%F-%T)"

echo "START k1c-0.75-1-b6c $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-1-b6c > data/eval_k1c-0.75-1-b6c.log 2>&1
echo "END k1c-0.75-1-b6c rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-1-b6c.jsonl)"

echo "START k1c-0.75-1-b6jc $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-1-b6jc > data/eval_k1c-0.75-1-b6jc.log 2>&1
echo "END k1c-0.75-1-b6jc rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-1-b6jc.jsonl)"

echo "START k1c-0.75-2-choice-obj $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-2-choice-obj > data/eval_k1c-0.75-2-choice-obj.log 2>&1
echo "END k1c-0.75-2-choice-obj rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-2-choice-obj.jsonl)"

echo "START k1c-0.75-2-b6c $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-2-b6c > data/eval_k1c-0.75-2-b6c.log 2>&1
echo "END k1c-0.75-2-b6c rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-2-b6c.jsonl)"

echo "START k1c-0.75-2-b6jc $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-2-b6jc > data/eval_k1c-0.75-2-b6jc.log 2>&1
echo "END k1c-0.75-2-b6jc rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-2-b6jc.jsonl)"

echo "START k1c-0.75-3-choice-obj $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-3-choice-obj > data/eval_k1c-0.75-3-choice-obj.log 2>&1
echo "END k1c-0.75-3-choice-obj rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-3-choice-obj.jsonl)"

echo "START k1c-0.75-3-b6c $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-3-b6c > data/eval_k1c-0.75-3-b6c.log 2>&1
echo "END k1c-0.75-3-b6c rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-3-b6c.jsonl)"

echo "START k1c-0.75-3-b6jc $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.75-3-b6jc > data/eval_k1c-0.75-3-b6jc.log 2>&1
echo "END k1c-0.75-3-b6jc rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.75-3-b6jc.jsonl)"

echo "START k1c-0.9-1-b6c $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.9-1-b6c > data/eval_k1c-0.9-1-b6c.log 2>&1
echo "END k1c-0.9-1-b6c rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.9-1-b6c.jsonl)"

echo "START k1c-0.9-1-b6jc $(date +%T)"
timeout 9000 python3 analysis/evaluate.py k1c-0.9-1-b6jc > data/eval_k1c-0.9-1-b6jc.log 2>&1
echo "END k1c-0.9-1-b6jc rc=$? $(date +%T) records=$(wc -l < data/android_k1c-0.9-1-b6jc.jsonl)"

echo "SUMMARIES $(date +%T)"
python3 analysis/k1_summary.py --class-level --alpha 0.1 > data/k1c_summary_a10.log 2>&1
python3 analysis/k1_summary.py --class-level --alpha 0.05 > data/k1c_summary_a05.log 2>&1
echo "QUEUE6-DONE $(date +%F-%T)"
