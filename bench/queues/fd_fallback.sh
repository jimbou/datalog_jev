#!/bin/bash
# F1: FlowDroid with bundled libraries excluded (bench/fd_fallback.py), the counterpart of our step-e fallback: its
# out-of-memory apps with the time left, then its successful apps with sinks as a control for silently lost leaks.
# Same per-run resources as bench/fd_budget.py: 16 GB heap, 4 threads, 2 runs in parallel on cores 0-7.
cd ~/receipts
echo "FDX-START $(date -u +%F-%T)" >> data/fd_fallback.log
FDB_JOBS=2 FDB_THREADS=4 FDB_XMX=16g taskset -c 0-7 python3 bench/fd_fallback.py data/fd_fallback.jsonl >> data/fd_fallback.log 2>&1
echo "FDX-DONE $(date -u +%F-%T)" >> data/fd_fallback.log
