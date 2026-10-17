#!/bin/bash
# G4 robustness: certify on the pooled populations (200 half splits, app_ltt.py), Jev and Sonnet 5.5 (pool390 only):
#   pool390 = 307 main + 83 IzzyOnDroid (full + fallback); pool456 = pool390 + the 66 F1-rescued apps (retry + fallback).
# Apps are kept apart by population suffix (no overlap: IzzyOnDroid excludes F-Droid packages; F1 apps failed the main build).
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
R=data/f3/g4_pool.txt
: > $R
for p in choice-obj sonnet55def3; do
  python3 - $p <<'PY'
import json, sys
p = sys.argv[1]
def emit(f, src, suf):
    for l in open(src):
        r = json.loads(l); r["app"] += suf; f.write(json.dumps(r) + "\n")
with open("data/android_fm-rk-%s_pool390.jsonl" % p, "w") as f:
    emit(f, "data/android_fm-rk-%s.jsonl" % p, "")
    emit(f, "data/android_fm-rk-%s_izzy.jsonl" % p, "#izzy")
    emit(f, "data/android_fm-rk-%s_izzy_fb.jsonl" % p, "#izzyfb")
import os
if not os.path.exists("data/android_fm-rk-%s_f1.jsonl" % p):
    sys.exit(0)  # no prices for the F1-rescued apps (Sonnet 5.5): pool390 only
with open("data/android_fm-rk-%s_pool456.jsonl" % p, "w") as f:
    for l in open("data/android_fm-rk-%s_pool390.jsonl" % p):
        f.write(l)
    emit(f, "data/android_fm-rk-%s_f1.jsonl" % p, "#f1")
    emit(f, "data/android_fm-rk-%s_f1e_fb.jsonl" % p, "#f1fb")
PY
  for pool in pool390 pool456; do
    [ -s data/android_fm-rk-${p}_$pool.jsonl ] || continue
    for a in 0.05 0.1; do
      echo "== fm-rk-${p}_$pool alpha $a" >> $R
      $C python3 analysis/app_ltt.py fm-rk-${p}_$pool --alpha $a 2>&1 | tail -n 2 >> $R
    done
  done
done
echo "POOL-DONE $(date -u +%F-%T)" >> $R
