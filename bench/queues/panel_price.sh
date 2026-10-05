#!/bin/bash
# Price every framework hole with a panel of other models (verbalized probabilities), then price the wording ablation.
# Needs OPENROUTERS_MINE in the environment (passed at launch, never written to disk).
cd "$HOME/receipts/probes" || exit 1
log() { echo "$1 $(date +%F-%T)" >> ../data/panel_price.log; }
log PRICE-START
export NO_REASONING=1
~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.8-27b q27 holes_android_fw > ../data/price_q27.log 2>&1 &
~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.7-flash qflash holes_android_fw > ../data/price_qflash.log 2>&1 &
~/ai-proxy/with-proxy python3 run_sonnet_price.py deepseek/deepseek-v4-flash-0731 dsflash holes_android_fw > ../data/price_dsflash.log 2>&1 &
unset NO_REASONING
~/ai-proxy/with-proxy python3 run_sonnet_price.py openai/gpt-5.6-luna luna holes_android_fw > ../data/price_luna.log 2>&1 &
~/ai-proxy/with-proxy python3 run_sonnet_price.py google/gemini-3.5-flash-lite gflash holes_android_fw > ../data/price_gflash.log 2>&1 &
wait
# a second pass fills methods whose answer failed the first time (the script skips the ones already priced)
export NO_REASONING=1
~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.8-27b q27 holes_android_fw >> ../data/price_q27.log 2>&1
~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.7-flash qflash holes_android_fw >> ../data/price_qflash.log 2>&1
~/ai-proxy/with-proxy python3 run_sonnet_price.py deepseek/deepseek-v4-flash-0731 dsflash holes_android_fw >> ../data/price_dsflash.log 2>&1
unset NO_REASONING
~/ai-proxy/with-proxy python3 run_sonnet_price.py openai/gpt-5.6-luna luna holes_android_fw >> ../data/price_luna.log 2>&1
~/ai-proxy/with-proxy python3 run_sonnet_price.py google/gemini-3.5-flash-lite gflash holes_android_fw >> ../data/price_gflash.log 2>&1
log "PANEL-PRICED q27=$(wc -l < ../data/jev_holes_android_fw_q27_r0.jsonl) qflash=$(wc -l < ../data/jev_holes_android_fw_qflash_r0.jsonl) dsflash=$(wc -l < ../data/jev_holes_android_fw_dsflash_r0.jsonl) luna=$(wc -l < ../data/jev_holes_android_fw_luna_r0.jsonl) gflash=$(wc -l < ../data/jev_holes_android_fw_gflash_r0.jsonl)"
# wording ablation: Jev's other two wordings for the methods added since they were first priced
~/ai-proxy/with-proxy python3 run_jev.py taint 0 all holes_android_fw > ../data/price_wording_taint.log 2>&1
~/ai-proxy/with-proxy python3 run_jev.py choice 0 all holes_android_fw > ../data/price_wording_choice.log 2>&1
log "WORDING-PRICED taint=$(wc -l < ../data/jev_holes_android_fw_taint_r0.jsonl) choice=$(wc -l < ../data/jev_holes_android_fw_choice_r0.jsonl)"
log PRICE-DONE
