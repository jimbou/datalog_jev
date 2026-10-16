#!/bin/bash
# F2: Jev with the written flow definition (wording choice-def in probes/run_jev.py) on the dev subset data/f2_dev.jsonl
# (5,094 methods, analysis/f2_dev.py). Approved by the user on 2026-10-16 (estimate $0.3-0.5; $5 left on OpenRouter).
# First 200 methods, then the rest; a guard stops the run above $1.50.
# Needs OPENROUTERS_MINE in the environment (passed at launch, never written to disk).
cd "$HOME/receipts/probes" || exit 1
L=~/receipts/data/f2/f2_jev_def.log
OUT=~/receipts/data/jev_f2_dev_choice-def_r0.jsonl
cost() { python3 -c "import json,sys; print('%.3f' % sum(json.loads(l).get('cost') or 0 for l in open(sys.argv[1])))" $OUT 2>/dev/null || echo 0; }
echo "JEVDEF-START $(date -u +%F-%T)" >> $L
~/ai-proxy/with-proxy python3 run_jev.py choice-def 0 200 f2_dev >> $L 2>&1
echo "JEVDEF-200 methods=$(wc -l < $OUT) cost=$(cost) $(date -u +%F-%T)" >> $L
( while sleep 30; do
    c=$(cost)
    if python3 -c "import sys; sys.exit(0 if float('$c') > 1.5 else 1)"; then
      P=$(pgrep -f "run_jev.py choice-def"); [ -n "$P" ] && kill $P; echo "JEVDEF-CAP cost=$c" >> $L; break
    fi
    pgrep -f "run_jev.py choice-def" > /dev/null || break
  done ) &
~/ai-proxy/with-proxy python3 run_jev.py choice-def 0 all f2_dev >> $L 2>&1
~/ai-proxy/with-proxy python3 run_jev.py choice-def 0 all f2_dev >> $L 2>&1
wait
echo "JEVDEF-DONE methods=$(wc -l < $OUT) cost=$(cost) $(date -u +%F-%T)" >> $L
