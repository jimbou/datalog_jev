#!/bin/bash
# TaintBench (experiment 3): build flow graphs for the 39 malware apps twice, with FlowDroid's default sources and sinks
# (same setting as the F-Droid calibration corpus, for the transfer test) and with TaintBench's own list (to match the
# documented leaks). Waits for the budgeted-verification chain.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/tb_chain.log; }
while ! grep -q VERIFY-DONE data/verify_chain.log 2>/dev/null; do sleep 120; done
log TB-START
export APK_LIST=bench/taintbench/apk_list.tsv APPS_FILE=bench/taintbench/apk_list.tsv JOBS=3 SOUFFLE_MEM_GB=16
GRAPHS_DIR=data/graphs_tb FAILED_FILE=data/tb_failed.txt ATTEMPTS_FILE=data/tb_attempts.txt \
  python3 analysis/run_android.py > data/tb_build_default.log 2>&1
log "TB-BUILT-DEFAULT graphs=$(ls data/graphs_tb | wc -l)"
SOURCES_SINKS=bench/taintbench/TB_SourcesAndSinks.txt GRAPHS_DIR=data/graphs_tbl FAILED_FILE=data/tbl_failed.txt ATTEMPTS_FILE=data/tbl_attempts.txt \
  python3 analysis/run_android.py > data/tb_build_tblist.log 2>&1
log "TB-BUILT-TBLIST graphs=$(ls data/graphs_tbl | wc -l)"
log TB-BUILD-DONE
