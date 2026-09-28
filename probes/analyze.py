"""Calibration analysis of Jev prices on library-flow atoms, focused on the low tail.

Usage: analyze.py WORDING [WORDING...]
"""
import collections, json, os, sys
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAUS = [0.02, 0.05, 0.1, 0.2]


def load(wording):
    rows = {(r["cls"], r["sig"]): r for r in map(json.loads, open(os.path.join(ROOT, "data/libflow.jsonl")))}
    reps = collections.defaultdict(list)
    for rep in range(3):
        path = os.path.join(ROOT, ("data/%s_r%d.jsonl" if wording.startswith("llm-") else "data/jev_%s_r%d.jsonl") % (wording, rep))
        if os.path.exists(path):
            for d in map(json.loads, open(path)):
                reps[(d["cls"], d["sig"])].append(d["p"])
    recs = []
    for key, ps in reps.items():
        r = rows[key]
        ps = np.array(ps)
        for k, a in enumerate(r["atoms"]):
            recs.append({"cls": r["cls"], "sig": r["sig"], "src": a["src"], "tgt": a["tgt"],
                         "y": int(a["label"]), "p": ps[:, k].mean(), "p0": ps[0, k],
                         "sd": ps[:, k].std() if len(ps) > 1 else 0.0, "n": len(ps)})
    return recs


def tail(p, y, name):
    print("  %-12s AUROC %.3f  ECE %.3f" % (name, roc_auc_score(y, p), ece(p, y)))
    for t in TAUS:
        m = p < t
        neg = (y == 0).sum()
        print("    p<%.2f: n=%4d  true-rate %.3f (must be <= ~%.3f)  false atoms captured %.1f%%"
              % (t, m.sum(), y[m].mean() if m.any() else float("nan"), p[m].mean() if m.any() else 0,
                 100 * (m & (y == 0)).sum() / neg))


def ece(p, y, bins=10):
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean()
               for b in range(bins) if (idx == b).any())


def reliability(p, y):
    edges = [0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.01]
    for lo, hi in zip(edges, edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.any():
            print("    [%.2f,%.2f) n=%4d mean-p %.3f true-rate %.3f" % (lo, hi, m.sum(), p[m].mean(), y[m].mean()))


def grouped_isotonic(recs, p):
    """Recalibrate with isotonic regression, cross-fitted by class (class = exchangeable unit)."""
    classes = sorted({r["cls"] for r in recs})
    rng = np.random.default_rng(0)
    fold = dict(zip(classes, rng.integers(0, 5, len(classes))))
    f = np.array([fold[r["cls"]] for r in recs])
    y = np.array([r["y"] for r in recs])
    out = np.zeros_like(p)
    for k in range(5):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p[f != k], y[f != k])
        out[f == k] = iso.predict(p[f == k])
    return out


def main():
    for w in sys.argv[1:]:
        recs = load(w)
        if not recs:
            continue
        y = np.array([r["y"] for r in recs])
        p = np.array([r["p"] for r in recs])
        p0 = np.array([r["p0"] for r in recs])
        sd = np.array([r["sd"] for r in recs])
        print("=== wording %s: %d atoms (%d true), repeats=%d, mean sd across repeats %.3f"
              % (w, len(y), y.sum(), min(r["n"] for r in recs), sd.mean()))
        tail(p0, y, "single call")
        tail(p, y, "mean of reps")
        print("  reliability (mean of reps):")
        reliability(p, y)
        piso = grouped_isotonic(recs, p)
        tail(piso, y, "isotonic-cv")
        print("  by target endpoint (mean of reps): AUROC / true-rate among p<0.1 / false captured <0.1")
        for tg in ("ret", "this", "arg"):
            m = np.array([r["tgt"].startswith(tg) for r in recs])
            lo = m & (p < 0.1)
            print("    %-5s n=%4d base %.2f AUROC %.3f  tr<.1 %.3f (n=%d)  cap %.1f%%"
                  % (tg, m.sum(), y[m].mean(), roc_auc_score(y[m], p[m]),
                     y[lo].mean() if lo.any() else float("nan"), lo.sum(),
                     100 * (lo & (y == 0)).sum() / max(1, (m & (y == 0)).sum())))
        order = np.argsort(p)
        print("  lowest-priced TRUE atoms (dangerous misses):")
        for i in [i for i in order if y[i]][:12]:
            r = recs[i]
            print("    %.3f  %s.%s  %s->%s" % (p[i], r["cls"], r["sig"], r["src"], r["tgt"]))
        print("  highest-priced FALSE atoms (possible label noise):")
        for i in [i for i in order[::-1] if not y[i]][:12]:
            r = recs[i]
            print("    %.3f  %s.%s  %s->%s" % (p[i], r["cls"], r["sig"], r["src"], r["tgt"]))


if __name__ == "__main__":
    main()
