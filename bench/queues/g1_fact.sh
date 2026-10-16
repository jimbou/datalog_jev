#!/bin/bash
# G1: language-model answers taken as library models on the main key (analysis/g1_fact.py): Jev at 0.5, GPT rubric
# labels (undecidable = no flow; and = flow as a sensitivity). Waits for the F2 dev queue; cores 12-15 at nice 10 only
# (cores 0-7: IzzyOnDroid build, 8-11: the user's other jobs).
cd ~/receipts
C="taskset -c 12-15 nice -n 10"
L=data/g1_fact.log
while pgrep -f "[f]2_dev_variants.sh" > /dev/null; do sleep 60; done
echo "G1-START $(date -u +%F-%T)" >> $L
$C python3 analysis/g1_fact.py prices >> $L
for t in jevfact gptfact gptfactu; do
  OUT_SUFFIX= JOBS=4 $C python3 analysis/evaluate.py fm-rk-$t > data/eval_fm-rk-$t.log 2>&1
  echo "EVAL $t rc=$? $(date -u +%F-%T)" >> $L
done
$C python3 analysis/g1_fact.py summary fm-rk-jevfact fm-rk-gptfact fm-rk-gptfactu >> $L
echo "G1-DONE $(date -u +%F-%T)" >> $L
