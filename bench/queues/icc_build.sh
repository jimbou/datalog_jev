#!/bin/bash
# Experiment 4: rebuild with inter-component (Intent) holes, from the APKs (stored facts lack class constants and manifests).
# The 80 FlowDroid-validation F-Droid apps (FlowDroid's default sources and sinks; calibration), then the TaintBench apps
# with TaintBench's list (documented leaks) and with the default list (transfer).
cd "$HOME/receipts" || exit 1
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1" PATH="$HOME/jdk/jdk-21.0.12.1+1/bin:$PATH" SCRATCH_DIR=/tmp
export FROM_APK=1 TAINT_DL=analysis/taint_icc.dl JOBS=3 SOUFFLE_MEM_GB=16
log() { echo "$1 $(date +%F-%T)" >> data/icc_chain.log; }
mkdir -p data/graphs_icc80c data/graphs_icc_tblc data/graphs_icc_tbc
log ICC-START
APPS_FILE=data/flowdroid/apps80.tsv GRAPHS_DIR=data/graphs_icc80c FAILED_FILE=data/icc80_failed_c.txt ATTEMPTS_FILE=data/icc80_attempts_c.txt \
  python3 analysis/run_android.py > data/icc_build_80.log 2>&1
log "ICC-BUILT-80 graphs=$(ls data/graphs_icc80c | wc -l)"
APK_LIST=bench/taintbench/apk_list.tsv APPS_FILE=bench/taintbench/apk_list.tsv SOURCES_SINKS=bench/taintbench/TB_SourcesAndSinks.txt \
  GRAPHS_DIR=data/graphs_icc_tblc FAILED_FILE=data/icc_tbl_failed_c.txt ATTEMPTS_FILE=data/icc_tbl_attempts_c.txt \
  python3 analysis/run_android.py > data/icc_build_tbl.log 2>&1
log "ICC-BUILT-TBL graphs=$(ls data/graphs_icc_tblc | wc -l)"
APK_LIST=bench/taintbench/apk_list.tsv APPS_FILE=bench/taintbench/apk_list.tsv \
  GRAPHS_DIR=data/graphs_icc_tbc FAILED_FILE=data/icc_tb_failed_c.txt ATTEMPTS_FILE=data/icc_tb_attempts_c.txt \
  python3 analysis/run_android.py > data/icc_build_tb.log 2>&1
log "ICC-BUILT-TB graphs=$(ls data/graphs_icc_tbc | wc -l)"
log ICC-BUILD-DONE
