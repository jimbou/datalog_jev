#!/bin/bash
# Experiment 4, after the build: price the inter-component holes with Sonnet 5 through Claude Code (no per-call cost), then
# evaluate library + inter-component holes with Jev and Sonnet library prices on the 80 F-Droid apps and on TaintBench.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/icc_chain.log; }
while ! grep -q ICC-BUILD-DONE data/icc_chain.log 2>/dev/null; do sleep 120; done
log ICC-PRICE-START
cd probes || exit 1
for g in icc80c icc_tblc icc_tbc; do
  BACKEND=claude PRICE_THREADS=4 python3 price_icc.py claude-sonnet-5 ../data/graphs_$g ../data/icc_prices_sonnet.jsonl >> ../data/icc_price.log 2>&1
done
cd .. || exit 1
log "ICC-PRICED rows=$(wc -l < data/icc_prices_sonnet.jsonl)"
export JOBS=3 ICC_PRICES=data/icc_prices_sonnet.jsonl
for g in icc80c icc_tblc icc_tbc; do
  for p in choice-obj sonnetp uniform; do
    GRAPHS_DIR=data/graphs_$g OUT_SUFFIX=_$g timeout 14400 python3 analysis/evaluate.py $p > data/eval_${p}_$g.log 2>&1
  done
  log "ICC-EVAL $g"
done
for p in choice-obj sonnetp; do
  python3 analysis/app_ltt.py ${p}_icc80c --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_${p}_icc80c_a05.log 2>&1
  python3 analysis/app_ltt.py ${p}_icc80c --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_${p}_icc80c_a1.log 2>&1
done
log ICC-EVAL-DONE
