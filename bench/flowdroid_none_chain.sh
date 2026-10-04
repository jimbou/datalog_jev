#!/bin/bash
# FlowDroid without library summaries on the same 40 apps, three at a time.
cd "$HOME/receipts" || exit 1
mkdir -p data/flowdroid_none
echo "FDN-START $(date +%F-%T)" >> data/flowdroid_none/progress.log
xargs -P 3 -L 1 bash bench/flowdroid_one_none.sh < data/flowdroid/apps.tsv
echo "FDN-DONE $(date +%F-%T)" >> data/flowdroid_none/progress.log
