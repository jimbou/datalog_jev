#!/bin/bash
# K2 generation, second plan: only the 145 receipt classes (a class summary includes its inherited methods),
# ordered by how many accepted verdicts depend on them, skipping classes whose log already ends with "Done.".
cd "$HOME/receipts" || exit 1
while pgrep -f "[m]ethodSummary.Main" > /dev/null; do sleep 30; done
echo "K2B-START $(date +%F-%T)" >> data/k2_progress.log
: > data/k2_classes2_todo.txt
while read -r c; do
  if ! grep -q "^Done\." "data/stubdroid_gen_logs/$c.log" 2>/dev/null; then echo "$c" >> data/k2_classes2_todo.txt; fi
done < data/k2_classes2_all.txt
xargs -P 3 -n 1 bash tools/k2_one2.sh < data/k2_classes2_todo.txt
echo "K2B-DONE $(date +%F-%T)" >> data/k2_progress.log
