#!/bin/bash
# Sonnet 5.5 (1 sample, definition) on every population, after the rescued apps' prices are complete:
# sonnet55def1 = samples[0] of sonnet55def3 (main + IzzyOnDroid) + the F1-rescued prices (cloud: data/f1_cloud/*.jsonl from
# branch last-cloud; server: f1_s55_server, f1_s55_rest2_rev), first price per method wins. The old dev-only def1 file is
# kept as .bak-dev. Evaluate on all graph sets, score the rescued apps with the main threshold (f1_score.py), certify
# the pools (373 = main + rescued, 390 = main + IzzyOnDroid, 456 = all). Cores 12-15, nice 10.
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/f1/s55_eval.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "WAIT"
until grep -q S55-REST-DONE data/f1/price_s55_rest.log 2>/dev/null; do sleep 120; done
log "START"
F=data/jev_holes_android_fw_sonnet55def1_r0.jsonl
[ -e $F.bak-dev ] || cp $F $F.bak-dev
python3 - >> $L <<'PY'
import json
out, seen = [], set()
def add(path, first_sample):
    n = 0
    for l in open(path):
        r = json.loads(l)
        p = r["samples"][0] if first_sample else r.get("p")
        k = (r["cls"], r["sig"])
        if p and k not in seen:
            seen.add(k); out.append({"cls": k[0], "sig": k[1], "p": p}); n += 1
    print(path, "added", n)
add("data/jev_holes_android_fw_sonnet55def3_r0.jsonl", True)
for f in ["data/f1_cloud/jev_f1_s55_cloud_sonnet55def1_r0.jsonl", "data/f1_cloud/jev_f1_s55_rest2_sonnet55def1_r0.jsonl",
          "data/jev_f1_s55_server_sonnet55def1_r0.jsonl", "data/jev_f1_s55_rest2_rev_sonnet55def1_r0.jsonl"]:
    add(f, False)
want = set()
for f in ["data/f1_s55_cloud.jsonl", "data/f1_s55_server.jsonl"]:
    want |= {(r["cls"], r["sig"]) for r in map(json.loads, open(f))}
print("rescued methods", len(want), "still unpriced", len(want - seen))
with open("data/jev_holes_android_fw_sonnet55def1_r0.jsonl", "w") as f:
    for r in out: f.write(json.dumps(r) + "\n")
print("sonnet55def1 total", len(out))
PY
for d in "" izzy izzy_fb f1 f1e_fb; do
  if [ -z "$d" ]; then G=data/graphs; S=; else G=data/graphs_$d; S=_$d; fi
  GRAPHS_DIR=$G OUT_SUFFIX=$S JOBS=4 $C python3 analysis/evaluate.py fm-rk-sonnet55def1 > data/f1/eval_sonnet55def1$S.log 2>&1
  log "EVAL '$d' rc=$? rows=$(wc -l < data/android_fm-rk-sonnet55def1$S.jsonl) warn=$(grep -c WARNING data/f1/eval_sonnet55def1$S.log)"
done
PRICERS=choice-obj,sonnetp,sonnet55def1 $C python3 analysis/f1_score.py "" > data/f1/s55_score.txt 2>&1
python3 - <<'PY'
import json
def emit(f, p, suf, tag):
    for l in open("data/android_fm-rk-%s%s.jsonl" % (p, suf)):
        r = json.loads(l); r["app"] += tag; f.write(json.dumps(r) + "\n")
parts = {"main": [("", "")], "izzy": [("_izzy", "#izzy"), ("_izzy_fb", "#izzyfb")], "f1": [("_f1", "#f1"), ("_f1e_fb", "#f1fb")]}
for p in ["sonnet55def1", "choice-obj"]:
    for pool, keys in [("pool373", ["main", "f1"]), ("pool390", ["main", "izzy"]), ("pool456", ["main", "izzy", "f1"])]:
        with open("data/android_fm-rk-%s_%s.jsonl" % (p, pool), "w") as f:
            for k in keys:
                for suf, tag in parts[k]: emit(f, p, suf, tag)
PY
R=data/f1/s55_pools.txt
: > $R
for name in fm-rk-sonnet55def1 fm-rk-sonnet55def1_pool373 fm-rk-sonnet55def1_pool390 fm-rk-sonnet55def1_pool456 \
            fm-rk-choice-obj_pool373 fm-rk-choice-obj_pool456; do
  for a in 0.05 0.1; do
    echo "== $name alpha $a" >> $R
    $C python3 analysis/app_ltt.py $name --alpha $a 2>&1 | tail -n 2 >> $R
  done
done
log "S55-EVAL-DONE"
