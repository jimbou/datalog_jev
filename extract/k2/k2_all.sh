#!/bin/bash
# Run the StubDroid generator over the K2 class list, 4 JVMs at a time, once the deletion queue is finished.
cd "$HOME/receipts" || exit 1
while pgrep -f "[o]vernight3.sh" > /dev/null; do sleep 30; done
echo "K2-START $(date +%F-%T)" >> data/k2_progress.log
xargs -P 4 -n 1 bash tools/k2_one.sh < data/k2_classes.txt
echo "K2-DONE $(date +%F-%T)" >> data/k2_progress.log
