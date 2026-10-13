#!/bin/bash
# F1 e on a subset (REMAINING_WORK.md): bundled third-party libraries (data/bundled_libs.txt) as library code, on the 40
# apps of data/f1e_subset.tsv (20 built, 20 failed; seeded draw). Same budget as FlowDroid in bench/fd_budget.py:
# 2100 s per app in all, 16 GB, 4 threads, two apps in parallel, pinned to cores 8-15 (the F1 d retry uses 0-7).
# Graphs in data/graphs_f1e; outcome, failing stage and seconds per app in data/f1/reasons_f1e.tsv.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/f1/f1e_subset.log; }
export JAVA_HOME=$HOME/jdk/jdk-21.0.12.1+1; export PATH=$JAVA_HOME/bin:$PATH
export JOBS=2 SOUFFLE_MEM_GB=16 SOUFFLE_THREADS=4 TOTAL_TIMEOUT=2100 EXTRACT_XMX=16g EXTRACT_THREADS=4 PYTHONUNBUFFERED=1
unset SOUFFLE_BIN
export LIB_PREFIXES=data/bundled_libs.txt GRAPHS_DIR=data/graphs_f1e
grep -v "^#" data/f1e_subset.tsv | cut -f1 > data/f1/f1e_apps.txt
grep -v "^#" data/f1e_subset.tsv | while IFS=$'\t' read -r app st apk; do
  for d in bench/apks data/fd_budget_apks; do [ -f "$d/$apk" ] && { printf '%s\t%s\n' "$app" "$d/$apk"; break; }; done
done > data/f1/f1e_apks.tsv
export APPS_FILE=data/f1/f1e_apps.txt APK_LIST=data/f1/f1e_apks.tsv
export FAILED_FILE=data/f1/failed_f1e.txt ATTEMPTS_FILE=data/f1/attempts_f1e.txt REASONS_FILE=data/f1/reasons_f1e.tsv
log "F1E-START apps=$(wc -l < data/f1/f1e_apps.txt) apks=$(wc -l < data/f1/f1e_apks.tsv)"
taskset -c 8-15 python3 analysis/run_android.py >> data/f1/build_f1e.log 2>&1
log "F1E-DONE built=$(ls data/graphs_f1e/*.npz 2>/dev/null | wc -l)"
