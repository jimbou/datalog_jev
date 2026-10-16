#!/bin/bash
# F2: evaluate a pricer variant on the development subset only (data/f2/dev_apps.txt, 92 of the 307 main apps).
# Usage: bash bench/queues/f2_eval_dev.sh TAG PRICEFILE   (PRICEFILE: data/jev_f2_dev_<tag>_r0.jsonl)
# Copies the dev prices to data/jev_holes_android_fw_<TAG>_r0.jsonl (a new file; methods outside the dev subset get
# evaluate.py's default 0.5, irrelevant for the dev apps), runs evaluate.py fm-rk-<TAG> (main graphs), keeps the dev
# apps' rows in data/android_fm-rk-<TAG>_dev.jsonl, and runs the 200-split calibration on them, next to the same
# for the main pricer choice-obj restricted to the dev apps.
set -e
cd ~/receipts
TAG=$1 PF=$2
[ -e data/jev_holes_android_fw_${TAG}_r0.jsonl ] && cmp -s "$PF" data/jev_holes_android_fw_${TAG}_r0.jsonl || cp -n "$PF" data/jev_holes_android_fw_${TAG}_r0.jsonl
OUT_SUFFIX=_f2all JOBS=4 taskset -c 8-15 python3 analysis/evaluate.py fm-rk-$TAG > data/f2/eval_$TAG.log 2>&1
for p in $TAG choice-obj; do
  src=data/android_fm-rk-$p.jsonl; [ $p = $TAG ] && src=data/android_fm-rk-${TAG}_f2all.jsonl
  python3 -c "
import json,sys
dev={l.strip() for l in open('data/f2/dev_apps.txt')}
with open('data/android_fm-rk-${p}_dev.jsonl','w') as f:
    for l in open('$src'):
        if json.loads(l)['app'] in dev: f.write(l)"
  for a in 0.05 0.1; do echo "== $p dev alpha $a"; python3 analysis/app_ltt.py fm-rk-${p}_dev --alpha $a | tail -n 2; done
done
