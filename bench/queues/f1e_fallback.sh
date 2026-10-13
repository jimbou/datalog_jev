#!/bin/bash
# F1 e as a fallback, within FlowDroid's budget: after the F1 d retry (bench/queues/f1_retry.sh) ends, every app that
# still failed on memory or time is built again with bundled libraries as library code (data/bundled_libs.txt), with
# only the time its full attempt left: 2100 s minus the seconds recorded in data/f1/reasons.tsv. Same 16 GB, 4 threads,
# two apps in parallel on 8 cores. The two attempts run one after the other, so memory never exceeds 16 GB at a time.
# Graphs in data/graphs_f1e_fb; outcomes in data/f1/reasons_fb.tsv; budgets in data/f1/fallback_budgets.tsv.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/f1/f1e_fallback.log; }
while pgrep -f "^bash bench/queues/[f]1_retry.sh" > /dev/null || pgrep -f "^bash bench/queues/[f]1e_attrib.sh" > /dev/null; do sleep 300; done
export JAVA_HOME=$HOME/jdk/jdk-21.0.12.1+1; export PATH=$JAVA_HOME/bin:$PATH
export JOBS=2 SOUFFLE_MEM_GB=16 SOUFFLE_THREADS=4 EXTRACT_XMX=16g EXTRACT_THREADS=4 PYTHONUNBUFFERED=1
unset SOUFFLE_BIN TOTAL_TIMEOUT
python3 - <<'PY'
last = {}
for l in open("data/f1/reasons.tsv"):
    a, why, s = l.rstrip("\n").split("\t")
    last[a] = (why, int(s))  # the latest attempt counts (the retry was restarted once)
rows = [(a, 2100 - s) for a, (why, s) in sorted(last.items()) if why != "ok" and ("memory" in why or "timeout" in why)]
rows = [(a, b) for a, b in rows if b > 60]
open("data/f1/fallback_budgets.tsv", "w").write("".join("%s\t%d\n" % r for r in rows))
open("data/f1/fallback_apps.txt", "w").write("".join(a + "\n" for a, _ in rows))
print(len(last), "apps in the retry,", len(rows), "get a fallback")
PY
export BUDGET_FILE=data/f1/fallback_budgets.tsv APPS_FILE=data/f1/fallback_apps.txt APK_LIST=data/f1/retry_apks.tsv
export LIB_PREFIXES=data/bundled_libs.txt GRAPHS_DIR=data/graphs_f1e_fb
export FAILED_FILE=data/f1/failed_fb.txt ATTEMPTS_FILE=data/f1/attempts_fb.txt REASONS_FILE=data/f1/reasons_fb.tsv
log "FB-START apps=$(wc -l < data/f1/fallback_apps.txt)"
taskset -c 0-7 python3 analysis/run_android.py >> data/f1/build_fb.log 2>&1
log "FB-DONE built=$(ls data/graphs_f1e_fb/*.npz 2>/dev/null | wc -l)"
