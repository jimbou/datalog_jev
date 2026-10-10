"""Summarize the same-budget comparison (bench/fd_budget.py): which apps finish under our pipeline and under FlowDroid.

Usage: python3 analysis/fd_budget_summary.py data/fd_budget.jsonl
"""
import json
import sys
from collections import Counter

recs = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
recs = [r for r in recs if r["base"]["state"] != "NoAPK"]
ok = lambda r, k: r[k]["state"] == "Success"
n = len(recs)
print("apps with an APK: %d (picked version replaced by the current one: %d)" % (n, sum(r["apk"] != r["picked_apk"] for r in recs)))
print("ours built: %d (%.0f%%)" % (sum(r["ours"] == "built" for r in recs), 100 * sum(r["ours"] == "built" for r in recs) / n))
print("FlowDroid with its models finished: %d (%.0f%%)" % (sum(ok(r, "base") for r in recs), 100 * sum(ok(r, "base") for r in recs) / n))
print("FlowDroid with holes open finished: %d (%.0f%%)" % (sum(ok(r, "holes") for r in recs), 100 * sum(ok(r, "holes") for r in recs) / n))
print("\ncross table (ours x FlowDroid with holes open):")
c = Counter((r["ours"], "fd-holes ok" if ok(r, "holes") else "fd-holes fail") for r in recs)
for k in sorted(c):
    print("  %-8s %-14s %d" % (k[0], k[1], c[k]))
print("\nFlowDroid failure reasons (base / holes):")
print("  base ", Counter(r["base"]["state"] for r in recs if not ok(r, "base")).most_common())
print("  holes", Counter(r["holes"]["state"] for r in recs if ok(r, "base") and not ok(r, "holes")).most_common())
both = [r for r in recs if ok(r, "base") and ok(r, "holes")]
if both:
    add = [r["holes"]["sinks"] - r["base"]["sinks"] for r in both if r["holes"]["sinks"] is not None and r["base"]["sinks"] is not None]
    print("\napps where FlowDroid finishes both runs: %d; holes add sinks in %d of them" % (len(both), sum(a > 0 for a in add)))
    t = sorted(r["base"]["seconds"] + r["holes"]["seconds"] for r in both)
    print("FlowDroid seconds for both runs: median %d" % t[len(t) // 2])
