#!/bin/bash
# F1: GPT rubric labels for the new hole methods, split out of f1_label.sh because gpt-6.1-sol returned
# "429 Too Many Requests" on the Codex account on 2026-10-14 (gpt-5.6-luna worked). Tests sol every 30 min with one
# small call, then labels with 2 threads; run_oracle.py resumes, so this can be restarted.
cd ~/receipts
L=~/receipts/data/f1/f1_label.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "GPT-WAIT"
until (cd /tmp && ~/.local/bin/codex exec --skip-git-repo-check --sandbox read-only -m gpt-6.1-sol "Say ok." 2>&1 | grep -q "^ok"); do
  sleep 1800
done
log "GPT-START"
cd probes
ORACLE_THREADS=2 PROMPT=rubric BACKEND=codex python3 run_oracle.py gpt-6.1-sol rubric-gpt61 holes_android_fw ../data/f1/rubric_methods_f1.tsv >> ../data/f1/rubric_gpt_f1.log 2>&1
log "GPT-LABELED $(wc -l < ../data/oracle-rubric-gpt61.jsonl)"
