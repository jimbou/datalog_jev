#!/bin/bash
# Finish the two incomplete panel pricers, then restart the panel evaluation. Qwen3.8-27B: the 390 missing methods on
# OpenRouter (user-approved, a few cents). gpt-5.6-luna: the 152 missing methods through Codex (no per-call cost).
cd "$HOME/receipts/probes" || exit 1
log() { echo "$1 $(date +%F-%T)" >> ../data/panel_price.log; }
NO_REASONING=1 PRICE_THREADS=4 ~/ai-proxy/with-proxy python3 run_sonnet_price.py qwen/qwen3.8-27b q27 holes_android_fw >> ../data/price_q27.log 2>&1 &
BACKEND=codex PRICE_THREADS=4 python3 run_sonnet_price.py gpt-5.6-luna luna holes_android_fw >> ../data/price_luna.log 2>&1 &
wait
log "FINISHED q27=$(wc -l < ../data/jev_holes_android_fw_q27_r0.jsonl) luna=$(wc -l < ../data/jev_holes_android_fw_luna_r0.jsonl) (luna's last methods via Codex)"
cd .. && setsid nohup bash bench/queues/panel_eval2.sh > data/panel_eval2.out 2>&1 < /dev/null &
