"""Program-level calibration of the acceptance threshold (Learn-then-Test, apps as units).

Loss of an app at threshold delta: 1 if some sink it accepts (bound <= delta) is a real flow.
Fixed-sequence testing over increasing delta with an exact binomial test of H: risk > alpha;
the chosen delta guarantees P(new app has a false accept) <= alpha with prob >= 1 - eps
(assuming apps are exchangeable). Evaluated by repeated random app splits.

Usage: app_ltt.py PRICING [--alpha A] [--eps E] [--splits K] [--deltas D1,D2,...]
  --deltas  threshold grid, strictest first (default: price grid; use 0.5,1,2,3 for uniform)
"""
import argparse, collections, json, os, random
from scipy.stats import binom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELTAS = [0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5]


def load(pricing):
    by_app = collections.defaultdict(list)
    for r in map(json.loads, open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing))):
        if r["bound"] is not None and r["truth_lo"] == r["truth_hi"]:
            by_app[r["app"]].append((r["bound"], r["truth_lo"]))
    return by_app


def loss(sinks, d):
    return any(real for b, real in sinks if b <= d)


def calibrate(apps, by_app, alpha, eps, deltas):
    n = len(apps)
    chosen = None
    for d in deltas:  # fixed sequence: stop at the first non-rejection
        k = sum(loss(by_app[a], d) for a in apps)
        if binom.cdf(k, n, alpha) <= eps:
            chosen = d
        else:
            break
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pricing")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--eps", type=float, default=0.1)
    ap.add_argument("--splits", type=int, default=200)
    ap.add_argument("--deltas", default=None)
    a = ap.parse_args()
    deltas = [float(x) for x in a.deltas.split(",")] if a.deltas else DELTAS
    by_app = load(a.pricing)
    apps = sorted(by_app)
    clean_total = {x: sum(not r for _, r in by_app[x]) for x in apps}
    print("pricing=%s apps=%d sinks=%d clean=%d" % (a.pricing, len(apps), sum(len(v) for v in by_app.values()),
                                                   sum(clean_total.values())))
    print("  per-delta: apps with a false accept / clean accepted (all apps)")
    for d in deltas:
        fa = sum(loss(by_app[x], d) for x in apps)
        acc = sum(sum(1 for b, r in by_app[x] if b <= d and not r) for x in apps)
        print("    delta=%.3f  apps-with-FA=%d/%d  clean accepted=%.3f" % (d, fa, len(apps), acc / max(1, sum(clean_total.values()))))
    rng = random.Random(0)
    viol = pw = none = 0
    chosen = collections.Counter()
    for _ in range(a.splits):
        sh = apps[:]
        rng.shuffle(sh)
        cal, test = sh[:len(sh) // 2], sh[len(sh) // 2:]
        d = calibrate(cal, by_app, a.alpha, a.eps, deltas)
        chosen[d] += 1
        if d is None:
            none += 1
            continue
        viol += sum(loss(by_app[x], d) for x in test) / len(test)
        tc = sum(clean_total[x] for x in test)
        pw += sum(1 for x in test for b, r in by_app[x] if b <= d and not r) / max(1, tc)
    k = a.splits - none
    print("  LTT alpha=%.2f eps=%.2f: splits with no valid delta=%d/%d; chosen deltas %s"
          % (a.alpha, a.eps, none, a.splits, dict(chosen)))
    if k:
        print("  held-out: mean per-app false-accept rate=%.3f (target <= %.2f)  mean power=%.3f" % (viol / k, a.alpha, pw / k))


if __name__ == "__main__":
    main()
