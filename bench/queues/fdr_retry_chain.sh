#!/bin/bash
# Fix 3, step 1: rerun the F-Droid apps whose FlowDroid receipt runs failed at FD_TIMEOUT=1200 with 3300 s and 24 GB
# (the first retry with 10 GB failed on memory), two shards.
# Failed records move to data/fd_receipts_fdroid_failed1200/ so that fd_receipts.py runs them again; finished FlowDroid
# outputs in data/fd_receipts_work are reused.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/fdr_retry_chain.log; }
export FD_TIMEOUT=3300 FD_XMX=24g
log FDRR-START
python3 - <<'EOF'
import glob, json, os
os.makedirs("data/fd_receipts_fdroid_failed1200", exist_ok=True)
names = []
for f in sorted(glob.glob("data/fd_receipts_fdroid/*.json")):
    if json.load(open(f)).get("status") == "failed":
        names.append(os.path.basename(f)[:-5])
        os.replace(f, os.path.join("data/fd_receipts_fdroid_failed1200", os.path.basename(f)))
ok = {os.path.basename(f)[:-5] for f in glob.glob("data/fd_receipts_fdroid/*.json")}  # only ok records are left here
names = sorted({os.path.basename(f)[:-5] for f in glob.glob("data/fd_receipts_fdroid_failed1200/*.json")} - ok)
lines = [l for l in open("data/fdr_fdroid.tsv").read().splitlines() if l.split("\t")[0] in set(names)]
open("data/fdr_retry.tsv", "w").write("\n".join(lines) + "\n")
print(len(names), "failed apps,", len(lines), "in the list")
EOF
split -n l/2 -d data/fdr_retry.tsv data/fdr_retry_shard
for i in 00 01; do
  python3 bench/fd_receipts.py data/fdr_retry_shard$i data/SourcesAndSinks.txt data/fd_receipts_fdroid 40 > data/fdr_retry$i.log 2>&1 &
done
wait
log "FDRR-DONE ok=$(grep -l '"status": "ok"' data/fd_receipts_fdroid/*.json | wc -l) failed=$(grep -l '"status": "failed"' data/fd_receipts_fdroid/*.json | wc -l)"
