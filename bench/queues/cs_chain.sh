#!/bin/bash
# Library-model case study: FlowDroid on the 39 TaintBench apps (TaintBench's sources and sinks) with its own summaries and
# with 50 extra summaries chosen by receipts, by app frequency and at random (probes/make_summaries.py).
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/cs_chain.log; }
log CS-START
for v in base receipts_50 frequency_50 random_50; do
  sum=data/summaries_$v; [ $v = base ] && sum=data/stubdroid
  awk -F'\t' -v v=$v -v s=$sum '{print v"\t"s"\tbench/taintbench/TB_SourcesAndSinks.txt\t"$1"\t"$2}' bench/taintbench/apk_list.tsv \
    | xargs -P 2 -L 1 -d '\n' sh -c 'IFS="	"; set -- $0; bash bench/flowdroid_cs.sh "$1" "$2" "$3" "$4" "$5"'
  log "CS-DONE $v $(wc -l < data/flowdroid_cs/$v/progress.log)"
done
log CS-ALL-DONE
