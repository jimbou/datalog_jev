#!/bin/bash
# FlowDroid validation: run the 40 selected apps, three at a time, once the final chain and the human-key rerun are done.
cd "$HOME/receipts" || exit 1
while ! grep -q AH-DONE data/final_chain.log 2>/dev/null; do sleep 60; done
echo "FD-START $(date +%F-%T)" >> data/flowdroid/progress.log
: > data/flowdroid/todo.tsv
while IFS=$'\t' read -r pkg apk; do
  if ! grep -q "^$pkg rc=.* xml=yes" data/flowdroid/progress.log 2>/dev/null; then printf '%s\t%s\n' "$pkg" "$apk" >> data/flowdroid/todo.tsv; fi
done < data/flowdroid/apps.tsv
xargs -P 3 -L 1 bash bench/flowdroid_one.sh < data/flowdroid/todo.tsv
echo "FD-DONE $(date +%F-%T)" >> data/flowdroid/progress.log
