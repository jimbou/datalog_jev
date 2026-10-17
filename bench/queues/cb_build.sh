#!/bin/bash
# F4a: callback holes (objects exposed to JavaScript, analysis/taint_cb.dl), built from the APKs like the Intent holes.
# 1. TaintBench with its own source/sink list (addJavascriptInterface is a sink there): do the documented leaks that were
#    cleared through addJavascriptInterface get reported?
# 2. Calibration set: the F-Droid and IzzyOnDroid apps of the main runs (full builds) whose dex mentions
#    addJavascriptInterface, built with FlowDroid's default list plus that sink.
# 3. Sonnet 5 prices for the callback facts (probes/price_cb.py, Claude Code), then Jev and Sonnet 5 (main setting, rubric
#    key) on both sets, the TaintBench comparison at the F-Droid thresholds, and LTT on the calibration set.
# Cores 8-15, nice 10.
cd "$HOME/receipts" || exit 1
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1" PATH="$HOME/jdk/jdk-21.0.12.1+1/bin:$PATH" SCRATCH_DIR=/tmp
export FROM_APK=1 TAINT_DL=analysis/taint_cb.dl JOBS=3 SOUFFLE_MEM_GB=16
C="taskset -c 8-15 nice -n 10"
L=data/cb/cb_chain.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
mkdir -p data/cb data/graphs_cb_tbl data/graphs_cb_fd
log CB-START
APK_LIST=bench/taintbench/apk_list.tsv APPS_FILE=bench/taintbench/apk_list.tsv SOURCES_SINKS=bench/taintbench/TB_SourcesAndSinks.txt \
  GRAPHS_DIR=data/graphs_cb_tbl FAILED_FILE=data/cb/tbl_failed.txt ATTEMPTS_FILE=data/cb/tbl_attempts.txt REASONS_FILE=data/cb/tbl_reasons.txt \
  $C python3 analysis/run_android.py > data/cb/build_tbl.log 2>&1
log "CB-BUILT-TBL graphs=$(ls data/graphs_cb_tbl | wc -l)"
# calibration apps: built fully in the main or IzzyOnDroid runs, dex mentions addJavascriptInterface
python3 - <<'PY'
import glob, os, zipfile
apks = {}
for pick in glob.glob("bench/apks/pick*.txt"):
    for line in open(pick).read().split("\n"):
        if line.count("\t") == 1 and "\x00" not in line:
            pkg, apk = line.split("\t")
            apks.setdefault(pkg, os.path.join("bench/apks", apk))
for line in open("data/f3/izzy_apks.tsv").read().splitlines():
    if line.count("\t") == 1:
        pkg, apk = line.split("\t")
        apks.setdefault(pkg, apk)
built = {os.path.basename(g)[:-4] for d in ("data/graphs", "data/graphs_izzy") for g in glob.glob(d + "/*.npz")}
keep, scanned = [], 0
for pkg in sorted(built):
    path = apks.get(pkg)
    if not path or not os.path.exists(path):
        continue
    scanned += 1
    try:
        with zipfile.ZipFile(path) as z:
            if any(b"addJavascriptInterface" in z.read(n) for n in z.namelist() if n.startswith("classes") and n.endswith(".dex")):
                keep.append((pkg, path))
    except Exception as e:
        print("skip", pkg, e)
with open("data/cb/js_apps.tsv", "w") as f:
    for pkg, path in keep:
        f.write("%s\t%s\n" % (pkg, path))
print("built apps", len(built), "scanned", scanned, "with addJavascriptInterface", len(keep))
PY
log "CB-SCAN $(wc -l < data/cb/js_apps.tsv) apps"
cp data/SourcesAndSinks.txt data/cb/SourcesAndSinks_js.txt
echo "<android.webkit.WebView: void addJavascriptInterface(java.lang.Object,java.lang.String)> -> _SINK_" >> data/cb/SourcesAndSinks_js.txt
APK_LIST=data/cb/js_apps.tsv APPS_FILE=data/cb/js_apps.tsv SOURCES_SINKS=data/cb/SourcesAndSinks_js.txt \
  GRAPHS_DIR=data/graphs_cb_fd FAILED_FILE=data/cb/fd_failed.txt ATTEMPTS_FILE=data/cb/fd_attempts.txt REASONS_FILE=data/cb/fd_reasons.txt \
  $C python3 analysis/run_android.py > data/cb/build_fd.log 2>&1
log "CB-BUILT-FD graphs=$(ls data/graphs_cb_fd | wc -l)"
for g in cb_tbl cb_fd; do
  (cd probes && BACKEND=claude PRICE_THREADS=4 python3 price_cb.py claude-sonnet-5 ../data/graphs_$g ../data/cb/prices_sonnet.jsonl >> ../data/cb/price.log 2>&1)
done
log "CB-PRICED $(wc -l < data/cb/prices_sonnet.jsonl)"
for p in choice-obj sonnetp; do
  for g in cb_tbl cb_fd; do
    CB_PRICES=data/cb/prices_sonnet.jsonl GRAPHS_DIR=data/graphs_$g OUT_SUFFIX=_$g JOBS=4 $C python3 analysis/evaluate.py fm-rk-$p > data/cb/eval_${p}_$g.log 2>&1
    log "EVAL $p $g rc=$? rows=$(wc -l < data/android_fm-rk-${p}_$g.jsonl)"
  done
done
R=data/cb/cb_results.txt
: > $R
for pd in "choice-obj 0.2" "sonnetp 0.02"; do
  set -- $pd
  echo "== TaintBench, $1, F-Droid threshold $2" >> $R
  CB_GRAPHS=data/graphs_cb_tbl python3 analysis/taintbench_compare.py data/android_fm-rk-$1_cb_tbl.jsonl bench/taintbench/TB_SourcesAndSinks.txt $2 >> $R 2>&1
  for a in 0.05 0.1; do
    echo "== calibration set, $1, alpha $a" >> $R
    $C python3 analysis/app_ltt.py fm-rk-$1_cb_fd --alpha $a 2>&1 | tail -n 2 >> $R
  done
done
log CB-DONE
