#!/bin/bash
# F1: labels and CLI prices for the new hole methods of the F1-rescued apps (retry graphs in data/graphs_f1, step-e
# fallback graphs in data/graphs_f1e_fb, whose bundled-library classes are holes).
# 1. Append the new methods to data/holes_android_fw.jsonl (probes/extend_holes_fw.py; backup .bak, old records unchanged).
# 2. Methods without a FlowDroid model (source none) not labeled before -> data/f1/rubric_methods_f1.tsv.
# 3. In parallel, free CLIs only (2026-10-14, the user: Claude via Claude Code, GPT via Codex):
#    Claude Code: rubric labels (Sonnet 5), then Sonnet verbalized prices (sonnetp)
#    Codex:       rubric labels (GPT 6.1), then gpt-5.6-luna prices (luna)
# Jev and the OpenRouter panel (q27, qflash, dsflash, gflash) are not run here: they need the user's approval.
cd ~/receipts
L=~/receipts/data/f1/f1_label.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "LABEL-START"
LIB_PREFIXES=data/bundled_libs.txt GRAPHS_DIRS=data/graphs_f1:data/graphs_f1e_fb python3 probes/extend_holes_fw.py >> $L 2>&1
python3 - <<'EOF'
import json
old = {tuple(l.rstrip("\n").split("\t")[:2]) for l in open("data/rubric_methods.tsv")}
new = [(r["cls"], r["sig"]) for r in map(json.loads, open("data/holes_android_fw.jsonl"))
       if r["source"] == "none" and (r["cls"], r["sig"]) not in old]
open("data/f1/rubric_methods_f1.tsv", "w").write("".join("%s\t%s\n" % k for k in new))
EOF
log "KEYS methods=$(wc -l < data/holes_android_fw.jsonl) to_label=$(wc -l < data/f1/rubric_methods_f1.tsv)"
cd probes
( ORACLE_THREADS=4 PROMPT=rubric BACKEND=claude python3 run_oracle.py claude-sonnet-5 rubric-sonnet5 holes_android_fw ../data/f1/rubric_methods_f1.tsv >> ../data/f1/rubric_sonnet_f1.log 2>&1
  log "SONNET-LABELED $(wc -l < ../data/oracle-rubric-sonnet5.jsonl)"
  BACKEND=claude PRICE_THREADS=4 python3 run_sonnet_price.py claude-sonnet-5 sonnetp holes_android_fw >> ../data/f1/price_sonnetp_f1.log 2>&1
  log "SONNETP-PRICED $(wc -l < ../data/jev_holes_android_fw_sonnetp_r0.jsonl)" ) &
( ORACLE_THREADS=4 PROMPT=rubric BACKEND=codex python3 run_oracle.py gpt-6.1-sol rubric-gpt61 holes_android_fw ../data/f1/rubric_methods_f1.tsv >> ../data/f1/rubric_gpt_f1.log 2>&1
  log "GPT-LABELED $(wc -l < ../data/oracle-rubric-gpt61.jsonl)"
  BACKEND=codex PRICE_THREADS=4 python3 run_sonnet_price.py gpt-5.6-luna luna holes_android_fw >> ../data/f1/price_luna_f1.log 2>&1
  log "LUNA-PRICED $(wc -l < ../data/jev_holes_android_fw_luna_r0.jsonl)" ) &
wait
log "LABEL-DONE"
