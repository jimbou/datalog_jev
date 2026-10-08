"""What clearing saves an analyst: alarms per app before and after clearing at a threshold.

Usage: python analysis/alarms_per_app.py <results.jsonl> <delta>

A hole-dependent sink (bound not None) is an alarm of the sound treatment of holes. It is a false alarm if the key says
no source reaches it, real if the key says one does, undecided otherwise. Clearing at delta removes alarms with
bound <= delta; cleared real alarms are wrong clearances.
"""
import json
import sys
from collections import defaultdict

import numpy as np

path, delta = sys.argv[1], float(sys.argv[2])
apps = defaultdict(lambda: {"false": 0, "false_left": 0, "real": 0, "real_cleared": 0, "und": 0, "und_left": 0,
                            "left_sizes": [], "cleared_sizes": []})
for line in open(path):
    r = json.loads(line)
    if r["bound"] is None:
        continue
    a = apps[r["app"]]
    left = r["bound"] > delta
    if r["truth_lo"] != r["truth_hi"]:
        a["und"] += 1
        a["und_left"] += left
    elif r["truth_lo"]:
        a["real"] += 1
        a["real_cleared"] += not left
    else:
        a["false"] += 1
        a["false_left"] += left
        (a["left_sizes"] if left else a["cleared_sizes"]).append(len(r["cut"]))

A = list(apps.values())
fb = np.array([a["false"] for a in A]); fa = np.array([a["false_left"] for a in A])
ub = np.array([a["und"] for a in A]); ua = np.array([a["und_left"] for a in A])
tb, ta = fb + ub + np.array([a["real"] for a in A]), fa + ua + np.array([a["real"] - a["real_cleared"] for a in A])
has = fb > 0
print("file %s delta %.2f apps with hole-dependent sinks %d" % (path, delta, len(A)))
print("false alarms: total %d -> %d (%.1f%% removed); apps with any %d -> %d" % (fb.sum(), fa.sum(), 100 * (1 - fa.sum() / fb.sum()), has.sum(), (fa > 0).sum()))
print("false alarms per app (apps with any): mean %.1f -> %.1f, median %.0f -> %.0f, p90 %.0f -> %.0f" % (
    fb[has].mean(), fa[has].mean(), np.median(fb[has]), np.median(fa[has]), np.percentile(fb[has], 90), np.percentile(fa[has], 90)))
print("apps whose false alarms all go: %d of %d" % (((fa == 0) & has).sum(), has.sum()))
print("undecided alarms: %d -> %d" % (ub.sum(), ua.sum()))
print("all alarms (real + false + undecided): %d -> %d; per app median %.0f -> %.0f" % (tb.sum(), ta.sum(), np.median(tb), np.median(ta)))
rb = sum(a["real"] for a in A); rc = sum(a["real_cleared"] for a in A)
print("real alarms: %d, cleared (wrong) %d (%.1f%%) in %d apps" % (rb, rc, 100 * rc / rb, sum(a["real_cleared"] > 0 for a in A)))
prec_b = rb / (rb + fb.sum()); prec_a = (rb - rc) / (rb - rc + fa.sum())
print("share of decided alarms that are real: %.1f%% -> %.1f%%" % (100 * prec_b, 100 * prec_a))
ls = np.array([s for a in A for s in a["left_sizes"]])
if len(ls):
    print("receipt size of remaining false alarms: 1: %.0f%%, <=4: %.0f%%, median %d" % (100 * (ls == 1).mean(), 100 * (ls <= 4).mean(), np.median(ls)))
