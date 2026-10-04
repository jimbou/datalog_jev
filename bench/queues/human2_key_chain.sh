#!/bin/bash
# Headline under the key with both human checks (pricing ah2-choice-obj), then its calibration at two risk levels.
cd "$HOME/receipts" || exit 1
export JOBS=6
echo "AH2-START $(date +%F-%T)" >> data/final_chain.log
timeout 14400 python3 analysis/evaluate.py ah2-choice-obj > data/eval_ah2-choice-obj.log 2>&1
echo "AH2-END rc=$? $(date +%F-%T)" >> data/final_chain.log
python3 analysis/app_ltt.py ah2-choice-obj --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_ah2-choice-obj_a05.log 2>&1
python3 analysis/app_ltt.py ah2-choice-obj --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_ah2-choice-obj_a1.log 2>&1
echo "AH2-DONE $(date +%F-%T)" >> data/final_chain.log
