#!/bin/bash
# G4: when the IzzyOnDroid build ends (IZZY-DONE in data/f3/f3_izzy.log), prepare the cloud job's input and push it.
# 1. Append the new hole methods of the IzzyOnDroid graphs (full and fallback) to data/holes_android_fw.jsonl
#    (probes/extend_holes_fw.py; backup .bak, old records unchanged).
# 2. data/f3_izzy.jsonl: hole records of the methods in these graphs that FlowDroid does not model and that lack a
#    Sonnet 5 rubric label (data/oracle-rubric-sonnet5.jsonl) or a sonnetp price.
# 3. Push it to main through ~/datalog_push (a GitHub clone; deploy key ~/.ssh/datalog_deploy, port 443). If the push
#    fails, the file stays in data/ and the log says PUSH-FAILED.
# Light work, cores 12-15 at nice 10. No model calls (GPT labels, luna and Jev prices wait for the user).
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/f3/f3_dataset.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "F3D-WAIT"
until grep -q IZZY-DONE data/f3/f3_izzy.log; do
  if ! pgrep -f "[f]3_izzy.sh" > /dev/null; then log "F3D-ABORT the build queue ended without IZZY-DONE"; exit 1; fi
  sleep 120
done
log "F3D-START $(grep IZZY-DONE data/f3/f3_izzy.log)"
LIB_PREFIXES=data/bundled_libs.txt GRAPHS_DIRS=data/graphs_izzy:data/graphs_izzy_fb $C python3 probes/extend_holes_fw.py >> $L 2>&1
$C python3 - >> $L 2>&1 <<'EOF'
import glob, json, sys
import numpy as np
sys.path.insert(0, "analysis")
from evaluate import MODELED
recs = {(r["cls"], r["sig"]): r for r in map(json.loads, open("data/holes_android_fw.jsonl"))}
g = set()
for p in glob.glob("data/graphs_izzy/*.npz") + glob.glob("data/graphs_izzy_fb/*.npz"):
    z = np.load(p, allow_pickle=True)
    g |= set(zip(z["hole_cls"].tolist(), z["hole_sub"].tolist()))
labeled = {(d["cls"], d["sig"]) for d in map(json.loads, open("data/oracle-rubric-sonnet5.jsonl")) if "labels" in d}
priced = {(d["cls"], d["sig"]) for d in map(json.loads, open("data/jev_holes_android_fw_sonnetp_r0.jsonl")) if d.get("p")}
un = [k for k in sorted(g) if k in recs and recs[k]["source"] not in MODELED and recs[k]["atoms"]]
todo = [k for k in un if k not in labeled or k not in priced]
with open("data/f3_izzy.jsonl", "w") as f:
    for k in todo:
        f.write(json.dumps(recs[k]) + "\n")
print("izzy graph methods %d, unmodeled %d, to label or price %d (no label %d, no sonnetp %d), candidate flows %d" % (
    len(g), len(un), len(todo), sum(k not in labeled for k in un), sum(k not in priced for k in un),
    sum(len(recs[k]["atoms"]) for k in todo)))
EOF
log "F3D-DATASET methods=$(wc -l < data/f3_izzy.jsonl)"
export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/datalog_deploy -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
P=$HOME/datalog_push
for i in 1 2 3 4 5 6; do
  if (cd $P && git fetch -q https://github.com/jimbou/datalog_jev.git main && git reset -q --hard FETCH_HEAD \
      && cp ~/receipts/data/f3_izzy.jsonl data/f3_izzy.jsonl && git add -f data/f3_izzy.jsonl \
      && git -c user.name=jimbou -c user.email=jimbou1999@gmail.com commit -q -m "G4: data/f3_izzy.jsonl, IzzyOnDroid methods to label and price ($(wc -l < data/f3_izzy.jsonl) methods), input of the cloud job

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" \
      && git push -q ssh://git@ssh.github.com:443/jimbou/datalog_jev.git HEAD:main) >> $L 2>&1; then
    log "F3D-PUSHED $(cd $P && git rev-parse --short HEAD)"; exit 0
  fi
  sleep 120
done
log "PUSH-FAILED (data/f3_izzy.jsonl is ready in ~/receipts/data)"
