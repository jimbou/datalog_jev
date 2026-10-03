#!/bin/bash
# Track K2: after the planned classes and the memory re-runs, extend StubDroid generation to all framework classes of the
# hole file (heaviest use first) until the deadline, then build the K2 labels.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/k2_progress.log; }
while ! grep -q K2C-DONE data/k2_progress.log 2>/dev/null; do sleep 60; done
export K2_DEADLINE=$(( $(date +%s) + 7 * 3600 ))
python3 - <<'PY' > data/k2_ext_classes.txt
import json, collections, os
w = collections.Counter()
for l in open("data/holes_android_fw.jsonl"):
    h = json.loads(l)
    w[h["cls"]] += h["apps"]
for c, _ in w.most_common():
    p = "data/stubdroid_gen_logs/%s.log" % c
    if os.path.exists(p) and any(x.startswith("Done.") for x in open(p, errors="replace")):
        continue
    print(c)
PY
log "K2X-START classes=$(wc -l < data/k2_ext_classes.txt)"
xargs -P 3 -n 1 bash tools/k2_one_ext.sh < data/k2_ext_classes.txt
while pgrep -f "[b]in/java -Xmx8g" > /dev/null; do sleep 30; done
python3 probes/k2_labels_all.py > data/k2_labels_all.log 2>&1
log "K2X-DONE"
