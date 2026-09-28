"""Evaluate the believe-then-bound pipeline on per-test results.

For each tau: an alarm is reported if SRC reaches SNK with code edges + candidates of
price >= tau. Unreported tests get the min-cut bound; a test is accepted as clean when
its bound <= delta. Reports recall of reported alarms, FDR among accepted, and power.
Usage: pipeline_eval.py PRICING
"""
import json, os, sys
import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taint

ROOT = taint.ROOT


def main():
    pricing = sys.argv[1]
    P = taint.Program()
    holes = {(r["cls"], r["sig"]): r for r in map(json.loads, open(os.path.join(ROOT, "data/holes.jsonl")))}
    prices = {}
    import collections
    acc = collections.defaultdict(list)
    for rep in range(3):
        for d in map(json.loads, open(os.path.join(ROOT, "data/jev_holes_%s_r%d.jsonl" % (pricing, rep)))):
            acc[(d["cls"], d["sig"])].append(d["p"])
    prices = {k: [sum(x) / len(x) for x in zip(*v)] for k, v in acc.items()}
    recs = [json.loads(l) for l in open(os.path.join(ROOT, "data/tests_%s.jsonl" % pricing))]
    taus = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7]
    deltas = [0.01, 0.05, 0.1, 0.2]
    res = {t: {"reported": 0, "tp": 0, "unrep_pos": [], "unrep_neg": []} for t in taus}
    for r in recs:
        G, cands, _, _ = taint.analyze(P, r["test"], r["cat"], holes, prices)
        for t in taus:
            rep = taint.reach(G, {c["mid"] for c in cands if c["p"] >= t})
            if rep:
                res[t]["reported"] += 1
                res[t]["tp"] += r["truth"]
            else:
                b = r["bound"] if r["bound"] is not None else float("inf")
                (res[t]["unrep_pos"] if r["truth"] else res[t]["unrep_neg"]).append(b)
    npos = sum(r["truth"] for r in recs)
    nneg = len(recs) - npos
    print("pricing=%s tests=%d truth-positive=%d truth-clean=%d" % (pricing, len(recs), npos, nneg))
    for t in taus:
        d = res[t]
        print(" tau=%.2f reported=%d (recall %.3f, precision %.3f)  unreported: %d pos, %d neg"
              % (t, d["reported"], d["tp"] / npos, d["tp"] / max(1, d["reported"]), len(d["unrep_pos"]), len(d["unrep_neg"])))
        for dl in deltas:
            ap = sum(b <= dl for b in d["unrep_pos"])
            an = sum(b <= dl for b in d["unrep_neg"])
            print("    delta=%.2f accepted=%d  false-accepts=%d  FDR=%.3f  power(clean accepted)=%.3f"
                  % (dl, ap + an, ap, ap / max(1, ap + an), an / max(1, nneg)))
        up = sorted(d["unrep_pos"])
        if up:
            print("    bounds on missed positives: min %.3f median %.3f" % (up[0], up[len(up) // 2]))


if __name__ == "__main__":
    main()
