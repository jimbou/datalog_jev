"""G3: cost and time per app.

Usage: python3 analysis/g3_cost.py [REASONS.tsv ...]
- Pricing: for each main graph (data/graphs), the unmodeled library methods it contains (holes in the fm- setting) and
  what pricing them costs with each pricer (the "cost" field of data/jev_holes_android_fw_<tag>_r0.jsonl; Sonnet is
  the API-equivalent of the CLI). Per app alone (nothing cached), and per new app when the corpus is already priced
  (methods first seen, apps in random order, seed 0, last 10% of apps).
- Build: seconds per successful full build under FlowDroid's budget, from the given reasons files ("ok" rows), next
  to FlowDroid's own seconds on the same budget (data/fd_budget.jsonl, runs with its models that succeeded).
"""
import glob
import json
import os
import random
import statistics
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from evaluate import MODELED, framework_holes  # noqa: E402

PRICERS = ("choice-obj", "sonnetp")


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def line(name, xs, fmt="%.4f"):
    print(("  %-34s median " + fmt + "  mean " + fmt + "  p90 " + fmt + "  max " + fmt + "  (n=%d)") % (
        name, statistics.median(xs), sum(xs) / len(xs), q(xs, 0.9), max(xs), len(xs)))


def main():
    fw = framework_holes()
    unmodeled = {k for k, h in fw.items() if h["source"] not in MODELED}
    cost = {}
    for t in PRICERS:
        cost[t] = {}
        for l in open(os.path.join(ROOT, "data/jev_holes_android_fw_%s_r0.jsonl" % t)):
            d = json.loads(l)
            cost[t][(d["cls"], d["sig"])] = d.get("cost") or 0.0
    apps = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data/graphs/*.npz"))):
        z = np.load(p, allow_pickle=True)
        apps[os.path.basename(p)[:-4]] = {(c, s) for c, s in zip(z["hole_cls"], z["hole_sub"])} & unmodeled
    print("Pricing, %d main graphs, %d distinct unmodeled methods" % (len(apps), len(set().union(*apps.values()))))
    line("unmodeled methods per app", [len(m) for m in apps.values()], "%.0f")
    for t in PRICERS:
        line("%s, one app alone ($)" % t, [sum(cost[t].get(k, 0) for k in m) for m in apps.values()])
    order = sorted(apps)
    random.Random(0).shuffle(order)
    seen, new = set(), []
    for a in order:
        new.append(apps[a] - seen)
        seen |= apps[a]
    tail = new[int(0.9 * len(new)):]
    line("new methods per app, last 10%", [len(m) for m in tail], "%.0f")
    for t in PRICERS:
        line("%s, new app, last 10%% ($)" % t, [sum(cost[t].get(k, 0) for k in m) for m in tail])
        print("  %-34s $%.2f" % ("%s, whole corpus" % t, sum(cost[t].get(k, 0) for k in seen)))
    ok = {}
    for f in sys.argv[1:]:
        for l in open(f):
            a, why, s = l.rstrip("\n").split("\t")
            if why == "ok":
                ok[a] = int(s)
    if ok:
        print("Build under FlowDroid's budget (%s)" % ", ".join(os.path.relpath(f, ROOT) for f in sys.argv[1:]))
        line("our build, seconds per app", list(ok.values()), "%.0f")
    fd = [json.loads(l) for l in open(os.path.join(ROOT, "data/fd_budget.jsonl"))]
    secs = [r["base"]["seconds"] for r in fd if r.get("base", {}).get("state") == "Success"]
    line("FlowDroid with its models, seconds", secs, "%.0f")
    both = [(ok[r["app"]], r["base"]["seconds"]) for r in fd if r["app"] in ok and r.get("base", {}).get("state") == "Success"]
    if both:
        line("  same apps: ours", [b[0] for b in both], "%.0f")
        line("  same apps: FlowDroid", [b[1] for b in both], "%.0f")


if __name__ == "__main__":
    main()
