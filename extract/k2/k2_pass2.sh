#!/bin/bash
# Second pass: re-run, with 16 GB and a 3 hour limit, the classes that ran out of memory or hit the time limit.
cd "$HOME/receipts" || exit 1
while ! grep -q K2B-DONE data/k2_progress.log 2>/dev/null; do sleep 60; done
: > data/k2_pass2_todo.txt
while read -r c; do
  f="data/stubdroid_gen_logs/$c.log"
  if [ -f "$f" ] && ! grep -q "^Done\." "$f" && grep -qE "OutOfMemoryError" "$f"; then echo "$c" >> data/k2_pass2_todo.txt; fi
  if ! [ -f "$f" ]; then echo "$c" >> data/k2_pass2_todo.txt; fi
done < data/k2_classes2_all.txt
echo "K2C-START $(date +%F-%T) classes=$(wc -l < data/k2_pass2_todo.txt)" >> data/k2_progress.log
xargs -P 2 -n 1 bash tools/k2_one_big.sh < data/k2_pass2_todo.txt
echo "K2C-DONE $(date +%F-%T)" >> data/k2_progress.log
