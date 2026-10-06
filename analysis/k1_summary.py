"""Summarize the deletion benchmark (K1): app-level LTT on every (rate, seed) run.

Usage: k1_summary.py [--alpha A] [--eps E] [--splits K]
Reads data/android_k1-<rate>-<seed>-<pricing>.jsonl and reports, per deletion rate and pricing,
the mean over seeds of the held-out share of apps with a wrong clearance and the share of
hard-slice leak-free verdicts cleared.
"""
import argparse, collections, glob, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_ltt import DELTAS, calibrate, load, loss, ROOT

UNIFORM_DELTAS = [0.5, 1, 2, 3]
FINE_DELTAS = [0.001, 0.002, 0.003, 0.004, 0.005, 0.0075] + DELTAS  # classifier prices are low


def run(pricing, alpha, eps, splits):
    by_app = load(pricing)
    apps = sorted(by_app)
    deltas = UNIFORM_DELTAS if pricing.endswith("uniform") else FINE_DELTAS if re.search(r"-b6", pricing) else DELTAS
    clean = {x: sum(not r for _, r in by_app[x]) for x in apps}
    rng = random.Random(0)
    viol = pw = k = over = 0
    for _ in range(splits):
        sh = apps[:]
        rng.shuffle(sh)
        cal, test = sh[:len(sh) // 2], sh[len(sh) // 2:]
        d = calibrate(cal, by_app, alpha, eps, deltas)
        if d is None:
            continue
        k += 1
        v = sum(loss(by_app[x], d) for x in test) / len(test)
        viol += v
        over += v > alpha  # what the guarantee bounds: at most eps of calibrations
        pw += sum(1 for x in test for b, r in by_app[x] if b <= d and not r) / max(1, sum(clean[x] for x in test))
    return {"apps": len(apps), "clean": sum(clean.values()), "real": sum(len(v) for v in by_app.values()) - sum(clean.values()),
            "fa": viol / k if k else None, "power": pw / k if k else 0.0, "certified": k / splits,
            "over": over / splits, "power_all": pw / splits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--eps", type=float, default=0.1)
    ap.add_argument("--splits", type=int, default=200)
    ap.add_argument("--class-level", action="store_true", help="read the class-level deletion runs (k1c-...)")
    a = ap.parse_args()
    tag = "k1c" if a.class_level else "k1"
    res = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(ROOT, "data/android_%s-*.jsonl" % tag))):
        m = re.match(r"android_(%s-([0-9.]+)-(\d+)-(.+))\.jsonl" % tag, os.path.basename(p))
        res[(float(m.group(2)), m.group(4))].append(run(m.group(1), a.alpha, a.eps, a.splits))
    print("K1%s deletion benchmark, alpha=%.2f eps=%.2f (mean over seeds)" % (" (whole classes deleted)" if a.class_level else "", a.alpha, a.eps))
    print("| Deleted | Pricer | Seeds | Hard-slice clean / real | Held-out apps with wrong clearance (certified splits) | Cleared (certified splits) | Certified splits | Splits with held-out wrong > alpha | Cleared (all splits) |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for (rate, pricing), rs in sorted(res.items()):
        fas = [r["fa"] for r in rs if r["fa"] is not None]
        print("| %d%% | %s | %d | %d / %d | %s | %.1f%% | %.0f%% | %.1f%% (max %.1f%%) | %.1f%% |" % (
            rate * 100, pricing, len(rs), sum(r["clean"] for r in rs) / len(rs), sum(r["real"] for r in rs) / len(rs),
            "%.1f%% (max %.1f%%)" % (100 * sum(fas) / len(fas), 100 * max(fas)) if fas else "n/a",
            100 * sum(r["power"] for r in rs) / len(rs), 100 * sum(r["certified"] for r in rs) / len(rs),
            100 * sum(r["over"] for r in rs) / len(rs), 100 * max(r["over"] for r in rs), 100 * sum(r["power_all"] for r in rs) / len(rs)))


if __name__ == "__main__":
    main()
