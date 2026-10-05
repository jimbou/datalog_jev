#!/bin/bash
# FlowDroid on 40 more apps (the next 40 of the same shuffled list): with its library summaries, then without.
cd "$HOME/receipts" || exit 1
python3 bench/flowdroid_select.py 40 8 40 data/flowdroid/apps2.tsv > data/flowdroid/select2.log 2>&1
echo "FDX-START $(date +%F-%T)" >> data/flowdroid/progress.log
xargs -P 2 -L 1 bash bench/flowdroid_one.sh < data/flowdroid/apps2.tsv
echo "FDX-SUMMARIES-DONE $(date +%F-%T)" >> data/flowdroid/progress.log
mkdir -p data/flowdroid_none
xargs -P 2 -L 1 bash bench/flowdroid_one_none.sh < data/flowdroid/apps2.tsv
echo "FDX-NONE-DONE $(date +%F-%T)" >> data/flowdroid_none/progress.log
