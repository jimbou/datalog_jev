#!/bin/bash
# F2 post-hoc variant (added 2026-10-16 after the dev results; report it as post-hoc): sonnet55def1 = the first of the
# three Sonnet 5.5 samples (no new calls), alone and in max(Jev, .), on the dev subset with the main key. Decides whether
# the rescued F1 apps' library methods need 3 samples ($132 estimated) or 1 ($44). Runs after g5_full.sh; cores 12-15.
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/f2/one_sample.log
until grep -q G5-DONE data/g5_full.log 2>/dev/null; do sleep 120; done
echo "START $(date -u +%F-%T)" >> $L
python3 -c "
import json
with open('data/jev_holes_android_fw_sonnet55def1_r0.jsonl', 'w') as f:
    for l in open('data/jev_f2_dev_sonnet55def3_r0.jsonl'):
        r = json.loads(l)
        f.write(json.dumps({'cls': r['cls'], 'sig': r['sig'], 'p': r['samples'][0]}) + '\n')"
$C python3 analysis/f2_combine.py max choice-obj sonnet55def1 max-cs55one >> $L
for t in sonnet55def1 max-cs55one; do
  OUT_SUFFIX=_f2all JOBS=4 $C python3 analysis/evaluate.py fm-rk-$t > data/f2/eval_rk_$t.log 2>&1
  python3 -c "
import json
dev = {l.strip() for l in open('data/f2/dev_apps.txt')}
with open('data/android_fm-rk-${t}_dev.jsonl', 'w') as f:
    for l in open('data/android_fm-rk-${t}_f2all.jsonl'):
        if json.loads(l)['app'] in dev: f.write(l)"
  for a in 0.05 0.1; do
    echo "== fm-rk-${t}_dev alpha $a" >> $L
    $C python3 analysis/app_ltt.py fm-rk-${t}_dev --alpha $a | tail -n 2 >> $L
  done
done
echo "DONE $(date -u +%F-%T)" >> $L
