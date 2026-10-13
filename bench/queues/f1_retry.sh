#!/bin/bash
# F1 d (REMAINING_WORK.md): retry the 253 apps our build failed on, with FlowDroid's budget from bench/fd_budget.py and
# nothing more: 2100 s per app for extraction and Soufflé together, 16 GB (Soot heap, Soufflé address space), 4 threads,
# two apps in parallel pinned to 8 cores. Soufflé runs as the interpreter: F1 c (compiled taint.dl) did not pay off
# (data/f1/mem_probe.tsv, systems.sieber.remotespotlight, 4 threads: interpreter 508 s / 13.9 GB max RSS, compiled
# without parallel loops 1153 s / 12.8 GB, compiled with `souffle -j 4` 461 s / 16.0 GB, over the limit in f1_check.sh).
# Each app uses the APK FlowDroid analyzed (data/f1/retry_apks.tsv, from data/fd_budget.jsonl). New graphs go to
# data/graphs_f1, so the paper's data/graphs stay untouched; outcome, failing stage and seconds per app in
# data/f1/reasons.tsv.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/f1/f1_retry.log; }
export JAVA_HOME=$HOME/jdk/jdk-21.0.12.1+1; export PATH=$JAVA_HOME/bin:$PATH
export JOBS=2 SOUFFLE_MEM_GB=16 SOUFFLE_THREADS=4 TOTAL_TIMEOUT=2100 EXTRACT_XMX=16g EXTRACT_THREADS=4 PYTHONUNBUFFERED=1
unset SOUFFLE_BIN
export APK_LIST=data/f1/retry_apks.tsv APPS_FILE=data/f1/retry_apps.txt GRAPHS_DIR=data/graphs_f1
export FAILED_FILE=data/f1/failed.txt ATTEMPTS_FILE=data/f1/attempts.txt REASONS_FILE=data/f1/reasons.tsv
log F1R-START
taskset -c 0-7 python3 analysis/run_android.py >> data/f1/build_retry.log 2>&1
log "F1R-DONE built=$(ls data/graphs_f1/*.npz 2>/dev/null | wc -l) failed=$(sort -u data/f1/failed.txt 2>/dev/null | wc -l)"
