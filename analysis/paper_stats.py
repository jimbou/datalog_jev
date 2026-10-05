"""Compact statistics behind the paper's figures, computed from the per-sink result files.

Usage: paper_stats.py OUT.json PRICING [PRICING ...]
For every pricing (data/android_<PRICING>.jsonl) it writes:
  curve     risk-coverage curve over all apps: for a sweep of thresholds, the share of leak-free hard-slice sinks cleared and the
            share of apps with at least one wrong clearance (threshold-free, so pricers on different scales are comparable);
  auroc     how well the bound ranks real flows above leak-free sinks (verdict level) and, per app, how well the smallest bound
            among an app's real flows ranks;
  learning  certified result against the number of calibration apps n (random subsets, tested on the other apps);
  certified the LTT result on half splits at alpha 0.05 and 0.1 (same grid as app_ltt.py, finer for classifier prices);
  sizes     receipt sizes of the cleared leak-free sinks at the alpha 0.05 threshold chosen on all apps.
"""
import bisect, collections, json, os, random, sys
import numpy as np
from scipy.stats import binom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COARSE = [0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5]
FINE = [0.001, 0.002, 0.003, 0.004, 0.005, 0.0075] + COARSE
COUNT = [0.5, 1, 2, 3, 4, 5]


def grid(pricing):
    base = pricing.split("-")[-1]
    if base == "uniform":
        return COUNT
    return FINE if base.startswith("b6") else COARSE


def load(pricing):
    apps = collections.defaultdict(lambda: ([], [], []))  # clean bounds, real bounds, clean receipt sizes
    for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing)):
        r = json.loads(l)
        if r["bound"] is None or r["truth_lo"] != r["truth_hi"]:
            continue
        a = apps[r["app"]]
        if r["truth_lo"]:
            a[1].append(r["bound"])
        else:
            a[0].append(r["bound"])
            a[2].append(len(r["cut"]) if r.get("cut") is not None else 0)
    out = {}
    for k, (c, rl, sz) in apps.items():
        order = np.argsort(c)
        out[k] = (np.asarray(c)[order], min(rl) if rl else float("inf"), np.asarray(sz)[order])
    return out


def cleared(data, apps, d):
    return sum(int(np.searchsorted(data[x][0], d, side="right")) for x in apps)


def wrong(data, apps, d):
    return sum(data[x][1] <= d for x in apps)


def calibrate(data, apps, alpha, eps, deltas):
    chosen = None
    for d in deltas:
        if binom.cdf(wrong(data, apps, d), len(apps), alpha) <= eps:
            chosen = d
        else:
            break
    return chosen


def auroc(pos, neg):
    """P(score of a real flow > score of a leak-free sink), ties count half."""
    pos, neg = np.sort(pos), np.sort(neg)
    if not len(pos) or not len(neg):
        return None
    lo = np.searchsorted(neg, pos, side="left")
    hi = np.searchsorted(neg, pos, side="right")
    return float((lo + 0.5 * (hi - lo)).sum() / (len(pos) * len(neg)))


def stats(pricing, eps=0.1):
    data = load(pricing)
    apps = sorted(data)
    tot = sum(len(data[x][0]) for x in apps)
    allb = np.concatenate([data[x][0] for x in apps] + [np.array([data[x][1] for x in apps if data[x][1] < float("inf")])])
    ths = sorted(set(np.quantile(allb, np.linspace(0, 1, 400)).tolist()) | set(grid(pricing)))
    curve = [(t, cleared(data, apps, t) / tot, wrong(data, apps, t) / len(apps)) for t in ths]
    real = []
    for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing)):
        r = json.loads(l)
        if r["bound"] is not None and r["truth_lo"] == r["truth_hi"] and r["truth_lo"]:
            real.append(r["bound"])
    clean = np.concatenate([data[x][0] for x in apps])
    res = {"apps": len(apps), "clean": tot, "real": len(real), "curve": curve,
           "auroc_verdict": auroc(np.asarray(real), clean)}
    # app level: does the smallest real bound of an app exceed the bounds of its leak-free sinks?
    res["auroc_app_mean"] = float(np.mean([auroc(np.array([data[x][1]]), data[x][0]) for x in apps
                                           if data[x][1] < float("inf") and len(data[x][0])]))
    rng = random.Random(0)
    cert = {}
    for alpha in (0.05, 0.1):
        v, p, none = [], [], 0
        for _ in range(200):
            sh = apps[:]
            rng.shuffle(sh)
            cal, test = sh[:len(sh) // 2], sh[len(sh) // 2:]
            d = calibrate(data, cal, alpha, eps, grid(pricing))
            if d is None:
                none += 1
                continue
            v.append(wrong(data, test, d) / len(test))
            p.append(cleared(data, test, d) / max(1, sum(len(data[x][0]) for x in test)))
        cert[str(alpha)] = {"wrong": v, "cleared": p, "abstain": none}
    res["certified"] = {k: {"wrong_mean": float(np.mean(c["wrong"])) if c["wrong"] else None,
                            "cleared_mean": float(np.mean(c["cleared"])) if c["cleared"] else 0.0,
                            "cleared_p5": float(np.percentile(c["cleared"], 5)) if c["cleared"] else 0.0,
                            "cleared_p95": float(np.percentile(c["cleared"], 95)) if c["cleared"] else 0.0,
                            "wrong_p95": float(np.percentile(c["wrong"], 95)) if c["wrong"] else None,
                            "abstain": c["abstain"]} for k, c in cert.items()}
    learn = []
    for n in (20, 40, 60, 80, 120, 160, 200, 240, 280):
        if n >= len(apps) - 20:
            continue
        for alpha in (0.02, 0.05, 0.1):
            v, p, none = [], [], 0
            for _ in range(200):
                sh = apps[:]
                rng.shuffle(sh)
                cal, test = sh[:n], sh[n:]
                d = calibrate(data, cal, alpha, eps, grid(pricing))
                if d is None:
                    none += 1
                    p.append(0.0)
                    continue
                v.append(wrong(data, test, d) / len(test))
                p.append(cleared(data, test, d) / max(1, sum(len(data[x][0]) for x in test)))
            learn.append({"n": n, "alpha": alpha, "cleared": float(np.mean(p)), "wrong": float(np.mean(v)) if v else None,
                          "abstain": none / 200})
    res["learning"] = learn
    d = calibrate(data, apps, 0.05, eps, grid(pricing))
    res["threshold_all_apps_a05"] = d
    if d is not None:
        sz = np.concatenate([data[x][2][:int(np.searchsorted(data[x][0], d, side="right"))] for x in apps])
        res["sizes"] = collections.Counter(int(min(s, 6)) for s in sz.tolist())
    return res


def main():
    out = {}
    for p in sys.argv[2:]:
        if not os.path.exists(os.path.join(ROOT, "data/android_%s.jsonl" % p)):
            print("missing", p, file=sys.stderr)
            continue
        out[p] = stats(p)
        c = out[p]["certified"]
        print(p, "apps", out[p]["apps"], "auroc %.3f" % out[p]["auroc_verdict"], "a05 cleared %.3f wrong %s" % (
            c["0.05"]["cleared_mean"], c["0.05"]["wrong_mean"]), flush=True)
        json.dump(out, open(sys.argv[1], "w"))


if __name__ == "__main__":
    main()
