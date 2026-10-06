#!/bin/bash
# Label-noise sensitivity (key/pricer separation, 2c): three keys in which 11% of the language-model "no" labels become "yes",
# evaluated with Jev and Sonnet prices. Waits for the inter-component build and the case-study FlowDroid runs.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/noise_chain.log; }
while ! grep -q ICC-BUILD-DONE data/icc_chain.log 2>/dev/null; do sleep 120; done
while ! grep -q CS-ALL-DONE data/cs_chain.log 2>/dev/null; do sleep 120; done
export JOBS=4
log NOISE-START
for s in 1 2 3; do
  for p in choice-obj sonnetp; do
    timeout 14400 python3 analysis/evaluate.py kn$s-$p > data/eval_kn$s-$p.log 2>&1
    python3 analysis/app_ltt.py kn$s-$p --alpha 0.05 --eps 0.1 --splits 200 > data/ltt_kn$s-${p}_a05.log 2>&1
    python3 analysis/app_ltt.py kn$s-$p --alpha 0.1 --eps 0.1 --splits 200 > data/ltt_kn$s-${p}_a1.log 2>&1
    log "END kn$s-$p"
  done
done
log NOISE-DONE
