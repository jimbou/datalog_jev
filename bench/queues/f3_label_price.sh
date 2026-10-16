#!/bin/bash
# G4: server half of the IzzyOnDroid labels and prices (approved by the user on 2026-10-16):
# 1. GPT-6.1 rubric labels via Codex for the 2,648 methods of data/f3_izzy.jsonl (about 24 GB of proxy traffic,
#    about 9 MB per call), 4 threads; run_oracle.py resumes.
# 2. Jev (choice-obj, the main wording) via OpenRouter for every hole method without a price (the new IzzyOnDroid
#    methods), estimate $0.10-0.20; a guard stops it above $1 for the methods not in holes_android_fw.jsonl.bak.
# luna prices are skipped for IzzyOnDroid (5% cleared on the main corpus; another 24 GB of traffic).
# Needs OPENROUTERS_MINE in the environment (passed at launch, never written to disk).
cd "$HOME/receipts/probes" || exit 1
L=~/receipts/data/f3/f3_label_price.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
python3 -c "
import json
with open('../data/f3/rubric_methods_f3.tsv', 'w') as f:
    for l in open('../data/f3_izzy.jsonl'):
        r = json.loads(l); f.write(r['cls'] + '\t' + r['sig'] + '\n')"
log "F3LP-START methods=$(wc -l < ../data/f3/rubric_methods_f3.tsv)"
cost() { python3 - <<'PY'
import json, os
os.chdir(os.path.expanduser("~/receipts/data"))
old = {(r["cls"], r["sig"]) for r in map(json.loads, open("holes_android_fw.jsonl.bak"))}
tot = 0.0
for l in open("jev_holes_android_fw_choice-obj_r0.jsonl"):
    try:
        d = json.loads(l)
    except ValueError:
        continue
    if (d["cls"], d["sig"]) not in old:
        tot += d.get("cost") or 0
print("%.3f" % tot)
PY
}
( ~/ai-proxy/with-proxy python3 run_jev.py choice-obj 0 all holes_android_fw >> ../data/f3/price_jev_f3.log 2>&1
  log "PRICED-JEV cost=$(cost)" ) &
J=$!
( while sleep 60; do
    kill -0 $J 2>/dev/null || break
    c=$(cost)
    if python3 -c "import sys; sys.exit(0 if float('$c') > 1 else 1)"; then
      pkill -f "run_jev.py choice-obj"; log "JEV-CAP cost=$c stopped"; break
    fi
  done ) &
ORACLE_THREADS=4 PROMPT=rubric BACKEND=codex python3 run_oracle.py gpt-6.1-sol rubric-gpt61 holes_android_fw ../data/f3/rubric_methods_f3.tsv >> ../data/f3/rubric_gpt_f3.log 2>&1
log "GPT-LABELED $(wc -l < ../data/oracle-rubric-gpt61.jsonl)"
wait
log "F3LP-DONE"
