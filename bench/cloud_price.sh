#!/bin/bash
# F2 pricing in a Claude Code cloud session (paper/CLOUD_CREDITS_PLAN.md): prices DATASET in chunks with
# probes/run_sonnet_price.py (BACKEND=claude, written flow definition, SAMPLES per method), commits and pushes the price
# file to BRANCH after every chunk (pushes are retried: cloud pushes sometimes fail with 403 and work later), and stops
# when the recorded API-equivalent cost of the file reaches CAP dollars. Restartable: priced methods are skipped.
# Usage: bash bench/cloud_price.sh MODEL TAG DATASET SAMPLES CAP BRANCH [CHUNK] [THREADS]
set -u
MODEL=$1 TAG=$2 DATASET=$3 SAMPLES=$4 CAP=$5 BRANCH=$6 CHUNK=${7:-250} THREADS=${8:-4}
OUT=data/jev_${DATASET}_${TAG}_r0.jsonl
N=$(wc -l < data/$DATASET.jsonl)
cost() { python3 -c "import json,sys; print('%.2f' % sum(json.loads(l).get('cost') or 0 for l in open(sys.argv[1])))" $OUT 2>/dev/null || echo 0; }
push() {
  for i in 1 2 3 4 5 6; do git push -q origin "$BRANCH" && return 0; echo "push failed ($i), retrying in 60 s"; sleep 60; done
  echo "PUSH FAILED: results are committed locally on $BRANCH"
}
if git ls-remote --exit-code --heads origin "$BRANCH" > /dev/null 2>&1; then  # resume on the pushed results
  git fetch -q origin "$BRANCH" && git checkout -q -B "$BRANCH" "origin/$BRANCH"
else
  git checkout -q -B "$BRANCH"
fi
for ((lim = CHUNK; ; lim += CHUNK)); do
  [ $lim -gt $N ] && lim=$N
  (cd probes && BACKEND=claude PRICE_PROMPT=definition SAMPLES=$SAMPLES PRICE_THREADS=$THREADS \
     python3 run_sonnet_price.py "$MODEL" "$TAG" "$DATASET" $lim)
  done_n=$(wc -l < $OUT 2>/dev/null || echo 0); c=$(cost)
  git add -f $OUT && git commit -q -m "F2 cloud pricing $TAG: $done_n of $N methods, \$$c API-equivalent" && push
  echo "$(date -u +%F-%T) CHUNK limit=$lim priced=$done_n of $N cost=\$$c"
  if python3 -c "import sys; sys.exit(0 if float('$c') >= float('$CAP') else 1)"; then echo "CAP reached (\$$c >= \$$CAP)"; break; fi
  [ $lim -ge $N ] && break
done
echo "DONE priced=$(wc -l < $OUT) of $N cost=\$$(cost)"
