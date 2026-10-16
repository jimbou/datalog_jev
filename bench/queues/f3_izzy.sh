#!/bin/bash
# F3 (second population, before the AndroZoo key arrives): the IzzyOnDroid apps of data/f3/izzy_picks.tsv
# (bench/izzy_select.py: F-Droid corpus criteria, not in F-Droid, all 134 eligible apps) through the same pipeline as F1:
# 1. download into bench/apks_izzy, SHA-256 checked against the index (only hashes go into the artifact);
# 2. full build with FlowDroid's budget (2100 s for extraction and Soufflé, 16 GB, 4 threads, 2 apps on cores 0-7),
#    graphs in data/graphs_izzy;
# 3. step-e fallback (bundled libraries as holes, data/bundled_libs.txt) for apps out of memory or time, with only the
#    time the full attempt left, graphs in data/graphs_izzy_fb.
cd "$HOME/receipts" || exit 1
L=data/f3/f3_izzy.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "IZZY-START picks=$(wc -l < data/f3/izzy_picks.tsv)"
mkdir -p bench/apks_izzy
: > data/f3/izzy_apks.tsv
while IFS=$'\t' read -r pkg apk sha; do
  f=bench/apks_izzy/$apk
  if [ ! -f "$f" ]; then
    curl -sfL --retry 5 --retry-all-errors -o "$f.part" "https://apt.izzysoft.de/fdroid/repo/$apk" && mv "$f.part" "$f"
  fi
  if [ -f "$f" ] && [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$sha" ]; then
    printf '%s\t%s\n' "$pkg" "$f" >> data/f3/izzy_apks.tsv
  else
    log "BAD-DOWNLOAD $pkg"; rm -f "$f" "$f.part"
  fi
done < data/f3/izzy_picks.tsv
cut -f1 data/f3/izzy_apks.tsv > data/f3/izzy_apps.txt
log "DOWNLOADED $(wc -l < data/f3/izzy_apks.tsv)"

export JAVA_HOME=$HOME/jdk/jdk-21.0.12.1+1; export PATH=$JAVA_HOME/bin:$PATH
export JOBS=2 SOUFFLE_MEM_GB=16 SOUFFLE_THREADS=4 EXTRACT_XMX=16g EXTRACT_THREADS=4 PYTHONUNBUFFERED=1
unset SOUFFLE_BIN LIB_PREFIXES BUDGET_FILE
TOTAL_TIMEOUT=2100 APK_LIST=data/f3/izzy_apks.tsv APPS_FILE=data/f3/izzy_apps.txt GRAPHS_DIR=data/graphs_izzy \
  FAILED_FILE=data/f3/failed.txt ATTEMPTS_FILE=data/f3/attempts.txt REASONS_FILE=data/f3/reasons.tsv \
  taskset -c 0-7 python3 analysis/run_android.py >> data/f3/build.log 2>&1
log "FULL-DONE built=$(ls data/graphs_izzy/*.npz 2>/dev/null | wc -l)"

python3 - <<'PY'
last = {}
for l in open("data/f3/reasons.tsv"):
    a, why, s = l.rstrip("\n").split("\t")
    last[a] = (why, int(s))
rows = [(a, 2100 - s) for a, (why, s) in sorted(last.items()) if why != "ok" and ("memory" in why or "timeout" in why)]
rows = [(a, b) for a, b in rows if b > 60]
open("data/f3/fallback_budgets.tsv", "w").write("".join("%s\t%d\n" % r for r in rows))
open("data/f3/fallback_apps.txt", "w").write("".join(a + "\n" for a, _ in rows))
print(len(last), "apps built or tried,", len(rows), "get a fallback")
PY
BUDGET_FILE=data/f3/fallback_budgets.tsv APPS_FILE=data/f3/fallback_apps.txt APK_LIST=data/f3/izzy_apks.tsv \
  LIB_PREFIXES=data/bundled_libs.txt GRAPHS_DIR=data/graphs_izzy_fb \
  FAILED_FILE=data/f3/failed_fb.txt ATTEMPTS_FILE=data/f3/attempts_fb.txt REASONS_FILE=data/f3/reasons_fb.tsv \
  taskset -c 0-7 python3 analysis/run_android.py >> data/f3/build_fb.log 2>&1
log "IZZY-DONE full=$(ls data/graphs_izzy/*.npz 2>/dev/null | wc -l) fallback=$(ls data/graphs_izzy_fb/*.npz 2>/dev/null | wc -l)"
