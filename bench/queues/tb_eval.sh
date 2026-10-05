#!/bin/bash
# Evaluate the TaintBench graphs (default source/sink list: graphs_tb; TaintBench's list: graphs_tbl) with Sonnet prices
# and counting; Jev is added once its prices for the new methods exist.
cd "$HOME/receipts" || exit 1
export JOBS=3
GRAPHS_DIR=data/graphs_tb OUT_SUFFIX=_tb timeout 3000 python3 analysis/evaluate.py sonnetp > data/eval_sonnetp_tb.log 2>&1
GRAPHS_DIR=data/graphs_tb OUT_SUFFIX=_tb timeout 3000 python3 analysis/evaluate.py uniform > data/eval_uniform_tb.log 2>&1
GRAPHS_DIR=data/graphs_tbl OUT_SUFFIX=_tbl timeout 3000 python3 analysis/evaluate.py sonnetp > data/eval_sonnetp_tbl.log 2>&1
GRAPHS_DIR=data/graphs_tbl OUT_SUFFIX=_tbl timeout 3000 python3 analysis/evaluate.py uniform > data/eval_uniform_tbl.log 2>&1
echo "TB-EVAL-DONE $(date +%F-%T)" >> data/tb_chain.log
