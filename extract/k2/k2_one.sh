#!/bin/bash
# StubDroid summary for one class of the real Android 13 implementation (android-all). Usage: k2_one.sh CLASS
CLS="$1"
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1"
cd "$HOME/receipts/tools/stubdroid" || exit 1
mkdir -p "$HOME/receipts/data/stubdroid_gen" "$HOME/receipts/data/stubdroid_gen_logs"
START=$(date +%s)
JAR=../witness/android-all-13-robolectric-9030017.jar
case "$CLS" in java.*|javax.*) JAR=../witness/jdk8-rt.jar ;; esac  # the Android jar has no java.* classes
timeout 3600 "$JAVA_HOME/bin/java" -Xmx8g -XX:ActiveProcessorCount=2 -cp "lib/*" soot.jimple.infoflow.methodSummary.Main \
  "$JAR" "$HOME/receipts/data/stubdroid_gen" "$CLS" -ct 900 -ft 60 -fo \
  > "$HOME/receipts/data/stubdroid_gen_logs/$CLS.log" 2>&1
echo "$CLS rc=$? $(( $(date +%s) - START ))s" >> "$HOME/receipts/data/k2_progress.log"
