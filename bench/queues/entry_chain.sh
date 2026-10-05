#!/bin/bash
# Rebuild the graphs of the 40 FlowDroid-validation apps with the entry-restricted analysis, evaluate them with Jev prices
# into separate files, and compare with FlowDroid again.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/entry_chain.log; }
log ENTRY-START
export TAINT_DL=analysis/taint_entry.dl GRAPHS_DIR=data/graphs_entry FAILED_FILE=data/entry_failed.txt ATTEMPTS_FILE=data/entry_attempts.txt
export APPS_FILE=data/flowdroid/apps.tsv JOBS=3 SOUFFLE_MEM_GB=16 SCRATCH_DIR=/tmp
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1" PATH="$HOME/jdk/jdk-21.0.12.1+1/bin:$PATH"
python3 analysis/run_android.py > data/entry_build.log 2>&1
log "ENTRY-BUILD-END graphs=$(ls data/graphs_entry/*.npz 2>/dev/null | wc -l)"
export JOBS=6 OUT_SUFFIX=_entry
python3 analysis/evaluate.py choice-obj > data/eval_choice-obj_entry.log 2>&1
log "ENTRY-EVAL-END records=$(wc -l < data/android_choice-obj_entry.jsonl)"
python3 bench/flowdroid_compare.py data/android_choice-obj_entry.jsonl > data/flowdroid_compare_entry.log 2>&1
python3 bench/flowdroid_compare.py data/android_choice-obj.jsonl > data/flowdroid_compare_orig.log 2>&1
log ENTRY-DONE
