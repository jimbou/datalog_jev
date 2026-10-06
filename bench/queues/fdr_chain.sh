#!/bin/bash
# Receipts on FlowDroid: 181 small F-Droid apps (FlowDroid's default sources and sinks) and the 39 TaintBench apps
# (TaintBench's list), two shards in parallel. Waits for the library-model case-study runs.
cd "$HOME/receipts" || exit 1
log() { echo "$1 $(date +%F-%T)" >> data/fdr_chain.log; }
while ! grep -q CS-ALL-DONE data/cs_chain.log 2>/dev/null; do sleep 120; done
export FD_TIMEOUT=1200
log FDR-START
printf "" > data/fdr_empty.tsv
python3 bench/fd_receipts.py data/fdr_empty.tsv data/SourcesAndSinks.txt data/fd_receipts_fdroid > data/fdr_prepare.log 2>&1  # builds the shared summary sets once
split -n l/2 -d data/fdr_fdroid.tsv data/fdr_fdroid_shard
python3 bench/fd_receipts.py data/fdr_fdroid_shard00 data/SourcesAndSinks.txt data/fd_receipts_fdroid 40 > data/fdr_fdroid0.log 2>&1 &
python3 bench/fd_receipts.py data/fdr_fdroid_shard01 data/SourcesAndSinks.txt data/fd_receipts_fdroid 40 > data/fdr_fdroid1.log 2>&1 &
wait
log "FDR-FDROID-DONE $(ls data/fd_receipts_fdroid | wc -l)"
split -n l/2 -d bench/taintbench/apk_list.tsv data/fdr_tb_shard
python3 bench/fd_receipts.py data/fdr_tb_shard00 bench/taintbench/TB_SourcesAndSinks.txt data/fd_receipts_tb 40 > data/fdr_tb0.log 2>&1 &
python3 bench/fd_receipts.py data/fdr_tb_shard01 bench/taintbench/TB_SourcesAndSinks.txt data/fd_receipts_tb 40 > data/fdr_tb1.log 2>&1 &
wait
log "FDR-TB-DONE $(ls data/fd_receipts_tb | wc -l)"
log FDR-DONE
