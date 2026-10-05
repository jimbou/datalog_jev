"""Summary of budgeted verification against the unverified baseline (paper RQ on checking assumptions).

Usage: verify_summary.py BASE VARIANT [VARIANT ...]     e.g. choice-obj choice-obj_vunlock_10 choice-obj_vunlock_25
Checking a fact has three effects: a "no" can make a leak-free sink independent of every remaining hole (cleared soundly,
it leaves the hole-dependent set), a "no" lowers bounds, and a "yes" turns a library flow into code, so real leaks become
reported and other receipts may have to use pricier facts. The share cleared is therefore measured against the leak-free
hard slice of the baseline: (soundly cleared by the checks + accepted at the certified threshold) / baseline leak-free,
on held-out apps over 200 half splits (alpha 0.05 and 0.1, eps 0.1). Also reported: real leaks the analysis now reports.
"""
import collections, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_ltt import DELTAS, ROOT, calibrate, load, loss


def per_app(pricing):
    clean, rep = collections.Counter(), collections.Counter()
    for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing)):
        r = json.loads(l)
        if r["truth_lo"] != r["truth_hi"]:
            continue
        if r["bound"] is None and r["truth_lo"]:
            rep[r["app"]] += 1
        elif r["bound"] is not None and not r["truth_lo"]:
            clean[r["app"]] += 1
    return clean, rep


def main():
    base, variants = sys.argv[1], sys.argv[2:]
    bclean, brep = per_app(base)
    apps = sorted(bclean)
    print("baseline %s: leak-free hard slice %d, reported real leaks %d" % (base, sum(bclean.values()), sum(brep.values())))
    print("| Variant | Soundly cleared by checks | Reported real leaks | alpha | Cleared (of baseline leak-free) | Held-out apps wrong |")
    print("| --- | --- | --- | --- | --- | --- |")
    for v in [base] + variants:
        by_app = load(v)
        vclean, vrep = per_app(v)
        sound = {a: max(0, bclean[a] - vclean.get(a, 0)) for a in apps}
        for alpha in (0.05, 0.1):
            rng = random.Random(0)
            cl, wr = [], []
            for _ in range(200):
                sh = apps[:]
                rng.shuffle(sh)
                cal, test = sh[:len(sh) // 2], sh[len(sh) // 2:]
                d = calibrate([a for a in cal if a in by_app], by_app, alpha, 0.1, DELTAS)
                acc = 0 if d is None else sum(1 for a in test for b, real in by_app.get(a, []) if b <= d and not real)
                cl.append((sum(sound[a] for a in test) + acc) / max(1, sum(bclean[a] for a in test)))
                wr.append(0.0 if d is None else sum(loss(by_app.get(a, []), d) for a in test) / len(test))
            print("| %s | %d | %d | %.2f | %.1f%% | %.1f%% |" % (v, sum(sound.values()), sum(vrep.values()), alpha,
                                                               100 * sum(cl) / len(cl), 100 * sum(wr) / len(wr)))


if __name__ == "__main__":
    main()
