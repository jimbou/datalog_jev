"""Sensitivity and validity checks of the program-level calibration (paper Table "calibration unit and sensitivity").

Usage: sensitivity.py PRICING [--alpha A] [--splits K] [--cluster-k N]
Reads data/android_<PRICING>.jsonl. For the same per-app losses it reports, as mean and 5th..95th percentile over random splits:
  - the share of held-out apps with a wrong clearance and the share of clean hole-dependent verdicts cleared, for
    epsilon in {0.05, 0.1, 0.2} and calibration share in {30, 50, 70}%;
  - nominal use without calibration (threshold = alpha) on all apps;
  - grouped splits: apps are linked when they share at least N third-party package prefixes (depth 3) among the methods that
    contain their sinks, linked apps form a cluster, and whole clusters go to one side of a split (apps that bundle the same
    library are then never on both sides).
"""
import argparse, collections, json, os, random, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_ltt import DELTAS, ROOT, calibrate, load, loss

OWN = ("android.", "androidx.", "java.", "javax.", "kotlin.", "kotlinx.", "dalvik.", "j$.", "dummyMainClass")


def prefixes(pricing):
    """app -> set of third-party package prefixes (depth 3) of the methods that contain its sinks."""
    out = collections.defaultdict(set)
    for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing)):
        r = json.loads(l)
        cls = r["site"][1:].split(":")[0]
        if cls.startswith(OWN) or cls.startswith(r["app"]):
            continue
        out[r["app"]].add(".".join(cls.split(".")[:3]))
    return out


def clusters(apps, pre, k):
    parent = {a: a for a in apps}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    members = collections.defaultdict(list)
    for a in apps:
        for p in pre.get(a, ()):
            members[p].append(a)
    shared = collections.Counter()
    for p, ms in members.items():
        if 1 < len(ms) <= 25:  # a prefix in very many apps would merge everything
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    shared[(ms[i], ms[j])] += 1
    for (a, b), n in shared.items():
        if n >= k:
            parent[find(a)] = find(b)
    groups = collections.defaultdict(list)
    for a in apps:
        groups[find(a)].append(a)
    return list(groups.values())


def run(by_app, apps, clean, alpha, eps, frac, splits, groups=None, seed=0):
    rng = random.Random(seed)
    viol, power = [], []
    for _ in range(splits):
        if groups:
            g = groups[:]
            rng.shuffle(g)
            cal, test, tot = [], [], len(apps)
            for grp in g:
                (cal if len(cal) < frac * tot else test).extend(grp)
        else:
            sh = apps[:]
            rng.shuffle(sh)
            cut = int(frac * len(sh))
            cal, test = sh[:cut], sh[cut:]
        d = calibrate(cal, by_app, alpha, eps, DELTAS)
        if d is None or not test:
            continue
        viol.append(sum(loss(by_app[x], d) for x in test) / len(test))
        tc = sum(clean[x] for x in test)
        power.append(sum(1 for x in test for b, real in by_app[x] if b <= d and not real) / max(1, tc))
    return viol, power


def fmt(v):
    return "%.1f%% [%.1f, %.1f]" % (100 * np.mean(v), 100 * np.percentile(v, 5), 100 * np.percentile(v, 95)) if v else "no threshold"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pricing")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--splits", type=int, default=200)
    ap.add_argument("--cluster-k", type=int, default=3)
    a = ap.parse_args()
    by_app = load(a.pricing)
    apps = sorted(by_app)
    clean = {x: sum(not r for _, r in by_app[x]) for x in apps}
    print("pricing=%s apps=%d alpha=%.2f; cells: wrong-clearance share [5th, 95th percentile over splits] | cleared share" % (a.pricing, len(apps), a.alpha))
    for eps in (0.05, 0.1, 0.2):
        for frac in (0.3, 0.5, 0.7):
            v, p = run(by_app, apps, clean, a.alpha, eps, frac, a.splits)
            print("  eps=%.2f calibration share=%d%%: wrong %s | cleared %s" % (eps, frac * 100, fmt(v), fmt(p)))
    fa = sum(loss(by_app[x], a.alpha) for x in apps)
    ca = sum(1 for x in apps for b, real in by_app[x] if b <= a.alpha and not real) / max(1, sum(clean.values()))
    print("  no calibration (threshold = alpha on all apps): %d of %d apps wrong, %.1f%% cleared" % (fa, len(apps), 100 * ca))
    pre = prefixes(a.pricing)
    groups = clusters(apps, pre, a.cluster_k)
    sizes = sorted((len(g) for g in groups), reverse=True)
    print("  clusters (share >= %d third-party package prefixes): %d clusters, largest %s, singletons %d" % (a.cluster_k, len(groups), sizes[:6], sum(1 for s in sizes if s == 1)))
    v, p = run(by_app, apps, clean, a.alpha, 0.1, 0.5, a.splits, groups=groups)
    print("  grouped splits (eps=0.10, 50%%): wrong %s | cleared %s (splits with a threshold: %d)" % (fmt(v), fmt(p), len(v)))


if __name__ == "__main__":
    main()
