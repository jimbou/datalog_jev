#!/bin/bash
# Rerun of the inter-component evaluation after adding the 5 framework methods the rebuilt graphs call (Sonnet labels and
# prices through Claude Code; Jev gives them the neutral price 0.5, see evaluate.py).
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/icc_chain.log; }
cp data/holes_android_fw.jsonl data/holes_android_fw.before_icc.jsonl
GRAPHS_DIRS=data/graphs_icc80c:data/graphs_icc_tblc:data/graphs_icc_tbc python3 probes/extend_holes_fw.py > data/icc_extend.log 2>&1
python3 - <<PY
import json
old = {(r["cls"], r["sig"]) for r in map(json.loads, open("data/holes_android_fw.before_icc.jsonl"))}
with open("data/icc_new_unmodeled.tsv", "w") as f:
    for r in map(json.loads, open("data/holes_android_fw.jsonl")):
        if (r["cls"], r["sig"]) not in old and r.get("source") == "none":
            f.write("%s\t%s\n" % (r["cls"], r["sig"]))
PY
cd probes && BACKEND=claude python3 run_oracle.py claude-sonnet-5 sonnet5-unk holes_android_fw ../data/icc_new_unmodeled.tsv >> ../data/icc_extend.log 2>&1
BACKEND=claude PRICE_THREADS=4 python3 run_sonnet_price.py claude-sonnet-5 sonnetp holes_android_fw >> ../data/icc_extend.log 2>&1
cd .. || exit 1
export JOBS=3 ICC_PRICES=data/icc_prices_sonnet.jsonl
for g in icc80c icc_tblc icc_tbc; do
  for p in choice-obj sonnetp uniform; do
    GRAPHS_DIR=data/graphs_$g OUT_SUFFIX=_$g timeout 14400 python3 analysis/evaluate.py $p > data/eval_${p}_$g.log 2>&1
  done
  log "ICC-EVAL2 $g $(wc -l < data/android_choice-obj_$g.jsonl)"
done
for p in choice-obj sonnetp; do
  python3 analysis/app_ltt.py ${p}_icc80c --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_${p}_icc80c_a1.log 2>&1
  python3 analysis/app_ltt.py ${p}_icc80c --alpha 0.2 --eps 0.1 --splits 200 > data/ltt_${p}_icc80c_a2.log 2>&1
done
log ICC-EVAL2-DONE
