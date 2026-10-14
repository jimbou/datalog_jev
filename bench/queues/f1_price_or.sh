#!/bin/bash
# F1: OpenRouter prices for the new hole methods of the F1-rescued apps (approved by the user on 2026-10-14, estimate
# $7.75, cap $10): Jev (choice-obj = main, taint, choice) and the panel (q27, qflash, dsflash, gflash), same commands as
# panel_price.sh / panel_price2.sh. The pricers resume, so only methods without a price are asked.
# A guard sums the recorded cost of the new methods (not in holes_android_fw.jsonl.bak) every minute and stops all
# OpenRouter pricers above $10.
# Needs OPENROUTERS_MINE in the environment (passed at launch, never written to disk).
cd "$HOME/receipts/probes" || exit 1
L=~/receipts/data/f1/f1_label.log
log() { echo "$1 $(date -u +%F-%T)" >> $L; }
cost() { python3 - <<'EOF'
import json, os
os.chdir(os.path.expanduser("~/receipts/data"))
old = {(r["cls"], r["sig"]) for r in map(json.loads, open("holes_android_fw.jsonl.bak"))}
tot = 0.0
for t in ["choice-obj", "taint", "choice", "q27", "qflash", "dsflash", "gflash"]:
    p = "jev_holes_android_fw_%s_r0.jsonl" % t
    for l in open(p):
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if (d["cls"], d["sig"]) not in old:
            tot += d.get("cost") or 0
print("%.3f" % tot)
EOF
}
log "OR-START cost=$(cost)"
( while sleep 60; do
    c=$(cost)
    if python3 -c "import sys; sys.exit(0 if float('$c') > 10 else 1)"; then
      P=$(pgrep -f "run_jev.py|run_sonnet_price.py (qwen|deepseek|google)/")
      [ -n "$P" ] && kill $P
      log "OR-CAP cost=$c stopped"
      break
    fi
    pgrep -f "run_jev.py|run_sonnet_price.py (qwen|deepseek|google)/" > /dev/null || break
  done ) &
for w in choice-obj taint choice; do
  ( ~/ai-proxy/with-proxy python3 run_jev.py $w 0 all holes_android_fw >> ../data/f1/price_jev_f1.log 2>&1
    log "PRICED-$w $(wc -l < ../data/jev_holes_android_fw_${w}_r0.jsonl)" ) &
done
panel() {  # model tag: first pass as in panel_price.sh, then fill failures without reasoning as in panel_price2.sh
  ~/ai-proxy/with-proxy python3 run_sonnet_price.py $1 $2 holes_android_fw >> ../data/f1/price_panel_f1.log 2>&1
  if [ $2 = gflash ]; then
    ~/ai-proxy/with-proxy python3 run_sonnet_price.py $1 $2 holes_android_fw >> ../data/f1/price_panel_f1.log 2>&1
  else
    NO_REASONING=1 ~/ai-proxy/with-proxy python3 run_sonnet_price.py $1 $2 holes_android_fw >> ../data/f1/price_panel_f1.log 2>&1
  fi
  log "PRICED-$2 $(wc -l < ../data/jev_holes_android_fw_$2_r0.jsonl)"
}
panel qwen/qwen3.8-27b q27 &
panel qwen/qwen3.7-flash qflash &
panel deepseek/deepseek-v4-flash-0731 dsflash &
panel google/gemini-3.5-flash-lite gflash &
wait
log "OR-DONE cost=$(cost)"
