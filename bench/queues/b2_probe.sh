#!/bin/bash
# B2 probe (approved 2026-10-17): receipts on FlowDroid itself with the holes scoped to our own flow graph of each app
# (fd_receipts.py, HOLE_SCOPE=data/graphs). Apps: the 7 that finished unscoped with hole-dependent sinks (to compare the
# sinks found) and the 30 that failed unscoped (to see how many now finish). Same budget as the main comparison:
# 2100 s and 16 GB per FlowDroid run, two apps in parallel on cores 0-3 and 4-7. Output data/fd_receipts_scoped.
cd ~/receipts
L=data/b2_probe.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
python3 - <<'PY'
import json, glob
apk = dict(l.rstrip("\n").split("\t")[:2] for l in open("data/fdr_fdroid.tsv") if "\t" in l)
recs = [json.load(open(p)) for p in glob.glob("data/fd_receipts_fdroid/*.json")]
hd = sorted(d["app"] for d in recs if d.get("status") == "ok" and d["on_only"])
failed = sorted(d["app"] for d in recs if d.get("status") != "ok")
apps = [a for a in hd + failed if a in apk]
for i in range(2):
    open("data/b2_probe_shard%d.tsv" % i, "w").write("".join("%s\t%s\n" % (a, apk[a]) for a in apps[i::2]))
print(len(hd), "compare apps,", len(failed), "failed apps,", len(apps), "with an APK")
PY
log "B2P-START $(cat data/b2_probe_shard0.tsv data/b2_probe_shard1.tsv | wc -l) apps"
export HOLE_SCOPE=data/graphs FD_XMX=16g FD_TIMEOUT=2100
taskset -c 0-3 python3 bench/fd_receipts.py data/b2_probe_shard0.tsv data/SourcesAndSinks.txt data/fd_receipts_scoped 40 > data/b2_probe0.log 2>&1 &
taskset -c 4-7 python3 bench/fd_receipts.py data/b2_probe_shard1.tsv data/SourcesAndSinks.txt data/fd_receipts_scoped 40 > data/b2_probe1.log 2>&1 &
wait
log "B2P-DONE $(ls data/fd_receipts_scoped | wc -l) apps"
