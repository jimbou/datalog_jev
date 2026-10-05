#!/bin/bash
# Second orchestrator for the pricer panel: the slow model gets more parallel requests, every model gets a "PRICED-<tag>" marker as soon
# as it is done (after a second pass for failed methods), and the wording ablation is priced in parallel.
# Needs OPENROUTERS_MINE in the environment (passed at launch, never written to disk).
cd "$HOME/receipts/probes" || exit 1
log() { echo "$1 $(date +%F-%T)" >> ../data/panel_price.log; }
log "PRICE2-START"
# the four fast models are already running (started by panel_price.sh); wait for each, then fill failed methods and mark it done
( while pgrep -f "run_sonnet_price.py qwen/qwen3.8-27b " > /dev/null; do sleep 20; done
  NO_REASONING=1 ~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.8-27b q27 holes_android_fw >> ../data/price_q27.log 2>&1
  log "PRICED-q27 methods=$(wc -l < ../data/jev_holes_android_fw_q27_r0.jsonl)" ) &
( while pgrep -f "run_sonnet_price.py qwen/qwen3.7-flash " > /dev/null; do sleep 20; done
  NO_REASONING=1 ~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.7-flash qflash holes_android_fw >> ../data/price_qflash.log 2>&1
  log "PRICED-qflash methods=$(wc -l < ../data/jev_holes_android_fw_qflash_r0.jsonl)" ) &
( while pgrep -f "run_sonnet_price.py deepseek/deepseek-v4-flash-0731 " > /dev/null; do sleep 20; done
  NO_REASONING=1 ~/ai-proxy/with-proxy python3 run_sonnet_price.py deepseek/deepseek-v4-flash-0731 dsflash holes_android_fw >> ../data/price_dsflash.log 2>&1
  log "PRICED-dsflash methods=$(wc -l < ../data/jev_holes_android_fw_dsflash_r0.jsonl)" ) &
( while pgrep -f "run_sonnet_price.py google/gemini-3.5-flash-lite " > /dev/null; do sleep 20; done
  ~/ai-proxy/with-proxy python3 run_sonnet_price.py google/gemini-3.5-flash-lite gflash holes_android_fw >> ../data/price_gflash.log 2>&1
  log "PRICED-gflash methods=$(wc -l < ../data/jev_holes_android_fw_gflash_r0.jsonl)" ) &
# the slow model: resume with 40 parallel requests, twice
( PRICE_THREADS=40 ~/ai-proxy/with-proxy python3 run_sonnet_price.py openai/gpt-5.6-luna luna holes_android_fw >> ../data/price_luna.log 2>&1
  PRICE_THREADS=40 ~/ai-proxy/with-proxy python3 run_sonnet_price.py openai/gpt-5.6-luna luna holes_android_fw >> ../data/price_luna.log 2>&1
  log "PRICED-luna methods=$(wc -l < ../data/jev_holes_android_fw_luna_r0.jsonl)" ) &
# wording ablation, in parallel
( ~/ai-proxy/with-proxy python3 run_jev.py taint 0 all holes_android_fw > ../data/price_wording_taint.log 2>&1
  ~/ai-proxy/with-proxy python3 run_jev.py choice 0 all holes_android_fw > ../data/price_wording_choice.log 2>&1
  log "PRICED-wording taint=$(wc -l < ../data/jev_holes_android_fw_taint_r0.jsonl) choice=$(wc -l < ../data/jev_holes_android_fw_choice_r0.jsonl)" ) &
wait
log "PRICE2-DONE"
