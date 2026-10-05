#!/bin/bash
# TaintBench with Jev: price the 108 framework methods TaintBench adds (user-approved, about 260 calls on OpenRouter), then
# evaluate both TaintBench graph sets. Needs OPENROUTERS_MINE in the environment.
cd "$HOME/receipts/probes" || exit 1
~/ai-proxy/with-proxy python3 run_jev.py choice-obj 0 all holes_android_fw > ../data/price_tb_jev.log 2>&1
cd .. || exit 1
export JOBS=3
GRAPHS_DIR=data/graphs_tb OUT_SUFFIX=_tb timeout 3000 python3 analysis/evaluate.py choice-obj > data/eval_choice-obj_tb.log 2>&1
GRAPHS_DIR=data/graphs_tbl OUT_SUFFIX=_tbl timeout 3000 python3 analysis/evaluate.py choice-obj > data/eval_choice-obj_tbl.log 2>&1
echo "TB-JEV-DONE $(date +%F-%T)" >> data/tb_chain.log
