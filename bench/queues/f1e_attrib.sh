#!/bin/bash
# F1 e attribution: the 9 previously failed subset apps that built with step e, built again WITHOUT step e (only the
# missing-facts fix and the F1 b budget), so a rescue is credited to step e only if this plain build fails.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/f1/f1e_attrib.log; }
export JAVA_HOME=$HOME/jdk/jdk-21.0.12.1+1; export PATH=$JAVA_HOME/bin:$PATH
export JOBS=2 SOUFFLE_MEM_GB=16 SOUFFLE_THREADS=4 TOTAL_TIMEOUT=2100 EXTRACT_XMX=16g EXTRACT_THREADS=4 PYTHONUNBUFFERED=1
unset SOUFFLE_BIN LIB_PREFIXES
python3 - <<'PY'
st = {l.split("\t")[0]: l.split("\t")[1] for l in open("data/f1e_subset.tsv") if not l.startswith("#")}
ok = [l.split("\t")[0] for l in open("data/f1/reasons_f1e.tsv") if l.split("\t")[1] == "ok"]
open("data/f1/attrib_apps.txt", "w").write("".join(a + "\n" for a in ok if st[a] == "failed"))
PY
export APPS_FILE=data/f1/attrib_apps.txt APK_LIST=data/f1/f1e_apks.tsv GRAPHS_DIR=data/graphs_f1e_plain
export FAILED_FILE=data/f1/failed_attrib.txt ATTEMPTS_FILE=data/f1/attempts_attrib.txt REASONS_FILE=data/f1/reasons_attrib.tsv
log "ATTRIB-START apps=$(wc -l < data/f1/attrib_apps.txt)"
taskset -c 8-15 python3 analysis/run_android.py >> data/f1/build_attrib.log 2>&1
log ATTRIB-DONE
