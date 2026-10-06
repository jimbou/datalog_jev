#!/bin/bash
# Library-model case study, round 2: models chosen by receipts on the TaintBench apps themselves (and frequency over the same
# apps, and random), 20 and 50 methods. Runs after round 1 and the inter-component build (memory).
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/cs_chain.log; }
while ! grep -q CS-ALL-DONE data/cs_chain.log 2>/dev/null; do sleep 120; done
while ! grep -q ICC-BUILD-DONE data/icc_chain.log 2>/dev/null; do sleep 120; done
for v in receipts_20_tb frequency_20_tb random_20_tb receipts_50_tb frequency_50_tb random_50_tb; do
  awk -F'\t' -v v=$v '{print v"\tdata/summaries_"v"\tbench/taintbench/TB_SourcesAndSinks.txt\t"$1"\t"$2}' bench/taintbench/apk_list.tsv \
    | xargs -P 1 -L 1 -d '\n' sh -c 'IFS="	"; set -- $0; bash bench/flowdroid_cs.sh "$1" "$2" "$3" "$4" "$5"'
  log "CS-DONE $v $(wc -l < data/flowdroid_cs/$v/progress.log)"
done
log CS2-ALL-DONE
