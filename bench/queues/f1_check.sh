#!/bin/bash
# F1 c: build 6 already-built apps with the Soufflé interpreter and with taint.dl compiled (tools/taint_bin/taint),
# same budget as FlowDroid in bench/fd_budget.py (2100 s per app in all, 16 GB, 4 threads, 2 apps in parallel on 8
# cores), then compare the graphs (analysis/compare_graphs.py) with each other and with the paper's data/graphs.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/f1/f1_check.log; }
export JAVA_HOME=$HOME/jdk/jdk-21.0.12.1+1; export PATH=$JAVA_HOME/bin:$PATH
export JOBS=2 SOUFFLE_MEM_GB=16 SOUFFLE_THREADS=4 TOTAL_TIMEOUT=2100 EXTRACT_XMX=16g EXTRACT_THREADS=4
export APPS_FILE=data/f1/check_apps.txt PYTHONUNBUFFERED=1
# usage: f1_check.sh [VARIANTS] (default "interp bin"); F1_BIN = compiled program (default tools/taint_bin_par/taint,
# generated with `souffle -j 4 -g`: without -j at generation time the generated code has no parallel loops)
F1_BIN=${F1_BIN:-$HOME/receipts/tools/taint_bin_par/taint}
for v in ${1:-interp bin}; do
  log "START $v"
  if [ $v != interp ]; then export SOUFFLE_BIN=$F1_BIN; else unset SOUFFLE_BIN; fi
  GRAPHS_DIR=data/f1/graphs_$v FAILED_FILE=data/f1/failed_$v.txt ATTEMPTS_FILE=data/f1/attempts_$v.txt \
    REASONS_FILE=data/f1/reasons_$v.tsv taskset -c 0-7 python3 analysis/run_android.py >> data/f1/build_$v.log 2>&1
  log "END $v"
  last=$v
done
python3 analysis/compare_graphs.py data/f1/graphs_interp data/f1/graphs_$last data/graphs >> data/f1/f1_check.log 2>&1
log COMPARE-DONE
# decisive check: the main evaluation on the compiled-program graphs gives the paper's per-sink results
GRAPHS_DIR=data/f1/graphs_$last OUT_SUFFIX=_f1check_$last JOBS=2 python3 analysis/evaluate.py fm-rk-choice-obj > data/f1/eval_f1check.log 2>&1
LAST=$last python3 - >> data/f1/f1_check.log 2>&1 <<'PY'
import json, os
key = lambda r: (r["app"], r["site"], json.dumps(r["bound"]), r["truth_lo"], r["truth_hi"], len(r["cut"]))
new = [json.loads(l) for l in open("data/android_fm-rk-choice-obj_f1check_%s.jsonl" % os.environ["LAST"])]
apps = {r["app"] for r in new}
old = [r for r in map(json.loads, open("data/android_fm-rk-choice-obj.jsonl")) if r["app"] in apps]
print(os.environ["LAST"], "evaluation on compiled graphs: %d sinks in %d apps, paper %d sinks; identical: %s"
      % (len(new), len(apps), len(old), len(new) > 0 and sorted(map(key, new)) == sorted(map(key, old))))
PY
log EVAL-DONE
