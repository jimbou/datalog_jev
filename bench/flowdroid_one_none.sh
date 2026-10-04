#!/bin/bash
# FlowDroid on one APK with NO library model (-tw NONE): taint stops at every call into library code that has no body,
# which is what "unsound by default" means. Same sources, sinks and limits as flowdroid_one.sh.
# Usage: flowdroid_one_none.sh PACKAGE APKFILE
PKG="$1"
APK="$2"
cd "$HOME/receipts" || exit 1
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1"
mkdir -p data/flowdroid_none/xml data/flowdroid_none/logs
START=$(date +%s)
timeout 3300 "$JAVA_HOME/bin/java" -Xmx10g -XX:ActiveProcessorCount=3 -cp "tools/flowdroid/lib/*" soot.jimple.infoflow.cmd.MainClass \
  -a "bench/apks/$APK" -p tools/flowdroid/platforms -s data/SourcesAndSinks.txt -tw NONE \
  -o "data/flowdroid_none/xml/$PKG.xml" -dt 2400 -ct 600 -rt 600 -mt 3 -ol \
  > "data/flowdroid_none/logs/$PKG.log" 2>&1
RC=$?
OK=no; [ -s "data/flowdroid_none/xml/$PKG.xml" ] && OK=yes
echo "$PKG rc=$RC xml=$OK $(( $(date +%s) - START ))s" >> data/flowdroid_none/progress.log
