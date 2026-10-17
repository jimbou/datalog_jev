#!/bin/bash
# Sonnet 5.5 (1 sample, definition) for the F1-rescued methods the cloud did not reach (data/f1_s55_rest2.jsonl, 2,274),
# after the server's own share (f1_s55_server) ends. The server takes them largest first (f1_s55_rest2_rev); the cloud's
# last credit takes them smallest first; duplicates are dropped when merging. Claude Code weekly credit.
cd ~/receipts/probes
while pgrep -f "sonnet55def1 f1_s55_server" > /dev/null; do sleep 120; done
BACKEND=claude PRICE_PROMPT=definition SAMPLES=1 PRICE_THREADS=4 python3 run_sonnet_price.py claude-sonnet-5-5 sonnet55def1 f1_s55_rest2_rev >> ../data/f1/price_s55_rest.log 2>&1
echo "S55-REST-DONE $(date -u +%F-%T)" >> ../data/f1/price_s55_rest.log
