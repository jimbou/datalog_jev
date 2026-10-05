"""Conformal selection of clean verdicts, evaluated leave-one-app-out.

Units: hole-dependent sink sites whose truth is determined. Score: min-cut bound (low = likely
clean). For each held-out app, calibrate on all other apps and test H_j: "sink j is a real flow"
with conformal p-values p_j = (1 + #{calib real flows with bound <= bound_j}) / (n + 1), then
Benjamini-Hochberg at level alpha (Jin & Candes, selection by prediction with conformal p-values).
Compared against the fixed threshold rule "accept if bound <= delta".

Usage: conformal.py PRICING [--tau T]
"""
import argparse, bisect, collections, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bh(pvals, alpha):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    k = 0
    for rank, i in enumerate(order, 1):
        if pvals[i] <= alpha * rank / len(pvals):
            k = rank
    return set(order[:k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pricing")
    ap.add_argument("--tau", default=None, help="only consider sinks unreported at this tau")
    a = ap.parse_args()
    R = [json.loads(l) for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % a.pricing))]
    U = [r for r in R if r["bound"] is not None and r["truth_lo"] == r["truth_hi"]]
    if a.tau:
        U = [r for r in U if not r["rep"][a.tau]]
    apps = sorted({r["app"] for r in U})
    print("pricing=%s tau=%s apps=%d units=%d real=%d clean=%d"
          % (a.pricing, a.tau, len(apps), len(U), sum(r["truth_lo"] for r in U), sum(not r["truth_lo"] for r in U)))
    for alpha in (0.01, 0.05, 0.1):
        sel = fd = clean_tot = 0
        per_app_fdp = []
        apps_wrong = 0
        for app in apps:
            cal = [r for r in U if r["app"] != app]
            test = [r for r in U if r["app"] == app]
            null_scores = sorted(r["bound"] for r in cal if r["truth_lo"])
            n = len(cal)
            p = [(1 + bisect.bisect_right(null_scores, r["bound"])) / (n + 1) for r in test]
            S = bh(p, alpha)
            f = sum(test[i]["truth_lo"] for i in S)
            sel += len(S)
            fd += f
            clean_tot += sum(not r["truth_lo"] for r in test)
            per_app_fdp.append(f / len(S) if S else 0.0)
            apps_wrong += f > 0
        print("  conformal alpha=%.2f selected=%d false=%d FDR(pooled)=%.4f mean per-app FDP=%.4f power=%.3f apps with a wrong clearance=%d/%d"
              % (alpha, sel, fd, fd / max(1, sel), sum(per_app_fdp) / max(1, len(apps)), (sel - fd) / max(1, clean_tot), apps_wrong, len(apps)))
    clean = sum(not r["truth_lo"] for r in U)
    for d in (0.05, 0.1, 0.2):
        acc = [r for r in U if r["bound"] <= d]
        f = sum(r["truth_lo"] for r in acc)
        print("  fixed delta=%.2f accepted=%d false=%d FDR=%.4f power=%.3f"
              % (d, len(acc), f, f / max(1, len(acc)), (len(acc) - f) / max(1, clean)))


if __name__ == "__main__":
    main()
