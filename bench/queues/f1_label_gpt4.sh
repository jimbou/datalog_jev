#!/bin/bash
# F1: after the luna prices finish on the Codex account, restart the GPT rubric labeler (f1_label_gpt.sh, 2 threads)
# with 4 threads. run_oracle.py resumes; killing it loses at most its unflushed output buffer (a few dozen labels).
cd ~/receipts
L=~/receipts/data/f1/f1_label.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
while pgrep -f "run_sonnet_price.py gpt-5.6-luna" > /dev/null; do sleep 300; done
P=$(pgrep -f "run_oracle.py gpt-6.1-sol")
[ -n "$P" ] && kill $P
sleep 10
log "GPT4-START labeled=$(wc -l < data/oracle-rubric-gpt61.jsonl)"
cd probes
ORACLE_THREADS=4 PROMPT=rubric BACKEND=codex python3 run_oracle.py gpt-6.1-sol rubric-gpt61 holes_android_fw ../data/f1/rubric_methods_f1.tsv >> ../data/f1/rubric_gpt_f1.log 2>&1
log "GPT4-DONE labeled=$(wc -l < ../data/oracle-rubric-gpt61.jsonl)"
