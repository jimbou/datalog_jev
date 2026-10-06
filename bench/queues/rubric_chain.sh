#!/bin/bash
# Relabel with the written flow definition (rubric prompt) by Sonnet 5 (Claude Code) and GPT-6.1 (Codex), after every
# currently queued job has finished. Methods: the 12,334 FlowDroid does not model plus those behind the person's checks.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/rubric_chain.log; }
while pgrep -f "[q]ueues/(noise_chain|gk_chain|icc_eval2|fdr_chain).sh" > /dev/null; do sleep 300; done
log RUBRIC-START
cat data/k4_unmodeled.tsv data/human_methods.tsv | sort -u > data/rubric_methods.tsv
cd probes || exit 1
for pass in 1 2; do  # the second pass fills methods whose answer failed
  PROMPT=rubric BACKEND=claude python3 run_oracle.py claude-sonnet-5 rubric-sonnet5 holes_android_fw ../data/rubric_methods.tsv >> ../data/rubric_sonnet.log 2>&1 &
  PROMPT=rubric BACKEND=codex python3 run_oracle.py gpt-6.1-sol rubric-gpt61 holes_android_fw ../data/rubric_methods.tsv >> ../data/rubric_gpt.log 2>&1 &
  wait
done
cd .. || exit 1
log "RUBRIC-DONE sonnet=$(wc -l < data/oracle-rubric-sonnet5.jsonl) gpt=$(wc -l < data/oracle-rubric-gpt61.jsonl) of $(wc -l < data/rubric_methods.tsv)"
