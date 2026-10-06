#!/bin/bash
# Key independent of Sonnet (2a): GPT-6.1 labels the methods FlowDroid does not model, through Codex; then Jev and Sonnet
# are evaluated under that key. Labels are written incrementally, so the labeling can be restarted.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/gk_chain.log; }
log GK-START
cd probes || exit 1
BACKEND=codex python3 run_oracle.py gpt-6.1-sol gpt61-unk holes_android_fw ../data/k4_unmodeled.tsv > ../data/gk_label.log 2>&1
BACKEND=codex python3 run_oracle.py gpt-6.1-sol gpt61-unk holes_android_fw ../data/k4_unmodeled.tsv >> ../data/gk_label.log 2>&1
cd .. || exit 1
log "GK-LABELED $(wc -l < data/oracle-gpt61-unk.jsonl)"
while pgrep -f "[q]ueues/(noise_chain|icc_eval).sh" > /dev/null; do sleep 300; done
export JOBS=4
for p in choice-obj sonnetp; do
  timeout 14400 python3 analysis/evaluate.py gk-$p > data/eval_gk-$p.log 2>&1
  python3 analysis/app_ltt.py gk-$p --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_gk-${p}_a05.log 2>&1
  python3 analysis/app_ltt.py gk-$p --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_gk-${p}_a1.log 2>&1
done
log GK-DONE
