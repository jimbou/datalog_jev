#!/bin/bash
# G4: after the cloud labels and prices (branch f3-cloud-izzy, files copied into data/ as *_izzycloud.jsonl) and the
# GPT labels (f3_label_price.sh) and the 148 Sonnet 5.5 prices past the cloud cap (server, Claude Code): merge the cloud files into the main label and price files (new methods only; backups
# .bak-g4), evaluate the IzzyOnDroid graphs (full: data/graphs_izzy, fallback: data/graphs_izzy_fb) with the main
# pricers, and score them with the thresholds certified on the 307 F-Droid apps (analysis/g4_score.py). Cores 12-15.
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/f3/g4_eval.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
log "G4E-START"
python3 - >> $L 2>&1 <<'PY'
import json, os, shutil
for src, dst in [("data/oracle-rubric-sonnet5-izzy_izzycloud.jsonl", "data/oracle-rubric-sonnet5.jsonl"),
                 ("data/jev_f3_izzy_sonnetp_r0_izzycloud.jsonl", "data/jev_holes_android_fw_sonnetp_r0.jsonl"),
                 ("data/jev_f3_izzy_sonnet55def3_r0_izzycloud.jsonl", "data/jev_holes_android_fw_sonnet55def3_r0.jsonl"),
                 ("data/jev_f3_izzy_s55rest_sonnet55def3_r0.jsonl", "data/jev_holes_android_fw_sonnet55def3_r0.jsonl")]:
    if not os.path.exists(dst + ".bak-g4"):
        shutil.copy(dst, dst + ".bak-g4")
    have = {(d["cls"], d["sig"]) for d in map(json.loads, open(dst))
            if d.get("labels") or d.get("p")}
    new = [l for l in open(src) if (lambda d: (d["cls"], d["sig"]) not in have and (d.get("labels") or d.get("p")))(json.loads(l))]
    with open(dst, "a") as f:
        f.writelines(new)
    print(dst, "added", len(new))
PY
for p in choice-obj sonnetp sonnet55def3 b6 freq uniform; do
  for d in izzy izzy_fb; do
    GRAPHS_DIR=data/graphs_$d OUT_SUFFIX=_$d JOBS=4 $C python3 analysis/evaluate.py fm-rk-$p > data/f3/eval_${p}_$d.log 2>&1
    log "EVAL-$p-$d rc=$? rows=$(wc -l < data/android_fm-rk-${p}_$d.jsonl)"
  done
done
$C python3 analysis/g4_score.py > data/f3/g4_score.txt 2>&1
log "G4E-DONE"
