#!/bin/bash
# FlowDroid on one APK with the same sources and sinks as our analysis and FlowDroid's default library summaries.
# Usage: flowdroid_one.sh PACKAGE APKFILE
PKG="$1"
APK="$2"
cd "$HOME/receipts" || exit 1
export JAVA_HOME="$HOME/jdk/jdk-21.0.12.1+1"
mkdir -p data/flowdroid/xml data/flowdroid/logs
START=$(date +%s)
timeout 3300 "$JAVA_HOME/bin/java" -Xmx10g -XX:ActiveProcessorCount=3 -cp "tools/flowdroid/lib/*" soot.jimple.infoflow.cmd.MainClass \
  -a "bench/apks/$APK" -p tools/flowdroid/platforms -s data/SourcesAndSinks.txt -tw STUBDROID -t data/stubdroid \
  -o "data/flowdroid/xml/$PKG.xml" -dt 2400 -ct 600 -rt 600 -mt 3 -ol \
  > "data/flowdroid/logs/$PKG.log" 2>&1
RC=$?
OK=no; [ -s "data/flowdroid/xml/$PKG.xml" ] && OK=yes
echo "$PKG rc=$RC xml=$OK $(( $(date +%s) - START ))s" >> data/flowdroid/progress.log
