#!/bin/bash
# FlowDroid for the library-model case study: one APK, one summary directory, one source/sink list.
# Usage: flowdroid_cs.sh VARIANT SUMMARY_DIR SOURCES_SINKS NAME APK_PATH
#   output: data/flowdroid_cs/VARIANT/{xml,logs}/NAME.*, progress in data/flowdroid_cs/VARIANT/progress.log
VAR="$1"; SUM="$2"; SS="$3"; NAME="$4"; APK="$5"
cd "$HOME/receipts" || exit 1
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1"
OUT="data/flowdroid_cs/$VAR"
mkdir -p "$OUT/xml" "$OUT/logs"
START=$(date +%s)
timeout 3300 "$JAVA_HOME/bin/java" -Xmx10g -XX:ActiveProcessorCount=3 -cp "tools/flowdroid/lib/*" soot.jimple.infoflow.cmd.MainClass \
  -a "$APK" -p tools/flowdroid/platforms -s "$SS" -tw STUBDROID -t "$SUM" \
  -o "$OUT/xml/$NAME.xml" -dt 2400 -ct 600 -rt 600 -mt 3 -ol \
  > "$OUT/logs/$NAME.log" 2>&1
RC=$?
OK=no; [ -s "$OUT/xml/$NAME.xml" ] && OK=yes
echo "$NAME rc=$RC xml=$OK $(( $(date +%s) - START ))s" >> "$OUT/progress.log"
