#!/bin/bash
# Numbers and figure data for the paper under the rubric key (the new main key).
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/rk_paper_chain.log; }
log RKP-START
# quick statistics first
python3 analysis/app_ltt.py rk-choice-obj --alpha 0.02 --eps 0.1 --splits 200 > data/ltt_rk-choice-obj_a02.log 2>&1
python3 analysis/sensitivity.py rk-choice-obj --alpha 0.05 --splits 200 > data/sensitivity_rk.log 2>&1
python3 analysis/conformal.py rk-choice-obj > data/conformal_rk.log 2>&1
python3 analysis/ablation_a1.py data/android_rk-choice-obj.jsonl --alpha 0.05 > data/ablation_a1_rk.log 2>&1
python3 - > data/counting_size1_rk.log 2>&1 <<PY
import json, collections
wrong, apps = collections.defaultdict(bool), set()
for l in open("data/android_rk-choice-obj.jsonl"):
    r = json.loads(l)
    if r["bound"] is None or r["truth_lo"] != r["truth_hi"]: continue
    apps.add(r["app"])
    if len(r["cut"]) == 1 and r["truth_lo"]: wrong[r["app"]] = True
print("apps", len(apps), "apps with a real one-fact receipt", sum(wrong.values()), "share %.3f" % (sum(wrong.values()) / len(apps)))
PY
python3 analysis/paper_stats.py data/paper_stats_rk.json rk-choice-obj rk-sonnetp rk-b6 rk-freq rk-uniform k2-choice-obj k2-sonnetp k2-b6 k2-b3 k2-uniform > data/paper_stats_rk.log 2>&1
log "RKP-STATS-DONE"
export JOBS=4
GRAPHS_DIR=data/graphs_tbl OUT_SUFFIX=_tbl timeout 3600 python3 analysis/evaluate.py rk-uniform > data/eval_rk-uniform_tbl.log 2>&1
for p in taint choice; do  # wording ablation under the rubric key
  timeout 14400 python3 analysis/evaluate.py rk-$p > data/eval_rk-$p.log 2>&1
  python3 analysis/app_ltt.py rk-$p --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_rk-${p}_a05.log 2>&1
  python3 analysis/app_ltt.py rk-$p --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_rk-${p}_a1.log 2>&1
  log "END rk-$p"
done
log RKP-DONE
