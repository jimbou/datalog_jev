"""Ablation A1: how the prices of a receipt's facts are combined into one bound.

Usage: ablation_a1.py [RESULTS_JSONL] [--alpha A] [--eps E] [--splits K]
Reads the per-sink records of a Jev-priced evaluation (default data/scale332/android_choice-obj.jsonl),
whose bound is the min-cut sum over cut edges, and recomputes the bound from the same cut four ways:
  sum_edges     ours: sum of prices over cut edges (a fact used at several call sites counts at each)
  sum_distinct  sum of prices over distinct facts of the cut (a union bound; valid and never looser)
  max_single    the largest single price (not a bound: it ignores that facts add up)
  independent   1 - prod(1 - p) over distinct facts (assumes the facts are independent)
Then runs the program-level Learn-then-Test of app_ltt.py on each (same splits) and reports the held-out
share of apps with a wrong clearance and the share of clean hard-slice verdicts cleared.
"""
import argparse, collections, json, math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_ltt import DELTAS, ROOT, calibrate, loss


def variants(cut):
    p = {}
    for c in cut:
        p[(c["cls"], c["sub"], c["k"], c["src"], c["tgt"])] = c["p"]
    ps = list(p.values())
    return {"sum_distinct": sum(ps), "max_single": max(ps), "independent": 1 - math.prod(1 - x for x in ps)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", default=os.path.join(ROOT, "data/scale332/android_choice-obj.jsonl"))
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--eps", type=float, default=0.1)
    ap.add_argument("--splits", type=int, default=200)
    a = ap.parse_args()
    names = ["sum_edges", "sum_distinct", "max_single", "independent"]
    by = {n: collections.defaultdict(list) for n in names}
    for l in open(a.results):
        r = json.loads(l)
        if r["bound"] is None or r["truth_lo"] != r["truth_hi"] or not r["cut"]:
            continue
        v = dict(variants(r["cut"]), sum_edges=r["bound"])
        for n in names:
            by[n][r["app"]].append((v[n], r["truth_lo"]))
    apps = sorted(by["sum_edges"])
    clean = {x: sum(not real for _, real in by["sum_edges"][x]) for x in apps}
    print("apps=%d hard-slice sinks=%d clean=%d  alpha=%.2f eps=%.2f splits=%d" % (
        len(apps), sum(len(v) for v in by["sum_edges"].values()), sum(clean.values()), a.alpha, a.eps, a.splits))
    print("%-13s %-18s %-12s %-12s | uncalibrated at delta=alpha: apps with a wrong clearance / cleared" % (
        "variant", "chosen delta", "wrong-clear", "cleared"))
    for n in names:
        rng = random.Random(0)
        viol = pw = none = 0
        chosen = collections.Counter()
        for _ in range(a.splits):
            sh = apps[:]
            rng.shuffle(sh)
            cal, test = sh[:len(sh) // 2], sh[len(sh) // 2:]
            d = calibrate(cal, by[n], a.alpha, a.eps, DELTAS)
            chosen[d] += 1
            if d is None:
                none += 1
                continue
            viol += sum(loss(by[n][x], d) for x in test) / len(test)
            tc = sum(clean[x] for x in test)
            pw += sum(1 for x in test for b, real in by[n][x] if b <= d and not real) / max(1, tc)
        k = a.splits - none
        top = ", ".join("%s:%d" % (kk, vv) for kk, vv in chosen.most_common(2))
        fa = sum(loss(by[n][x], a.alpha) for x in apps)
        ca = sum(1 for x in apps for b, real in by[n][x] if b <= a.alpha and not real) / sum(clean.values())
        print("%-13s %-18s %-12s %-12s | %d of %d apps (%.1f%%) / %.1f%%" % (
            n, top, "%.1f%%" % (100 * viol / k) if k else "no delta", "%.1f%%" % (100 * pw / k) if k else "-",
            fa, len(apps), 100 * fa / len(apps), 100 * ca))


if __name__ == "__main__":
    main()
