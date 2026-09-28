"""Evaluate the believe-then-bound pipeline on Android sink sites.

Usage: android_eval.py PRICING
Reads data/android_<PRICING>.jsonl. A sink's truth is determined when it agrees with
unknown-label hole facts both off (truth_lo) and on (truth_hi).
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    pricing = sys.argv[1]
    R = [json.loads(l) for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing))]
    hole = [r for r in R if r["bound"] is not None]
    det = [r for r in hole if r["truth_lo"] == r["truth_hi"]]
    print("pricing=%s apps=%d reachable sinks=%d code-only=%d hole-dependent=%d (truth determined %d: %d real, %d clean)"
          % (pricing, len({r["app"] for r in R}), len(R), len(R) - len(hole), len(hole), len(det),
             sum(r["truth_lo"] for r in det), sum(not r["truth_lo"] for r in det)))
    clean = [r for r in det if not r["truth_lo"]]
    real = [r for r in det if r["truth_lo"]]
    print("  cut size (facts) on clean sinks:", sorted(collections.Counter(len(r["cut"]) for r in clean).items())[:15])
    print("  bound quantiles on clean sinks:", quant([r["bound"] for r in clean]))
    print("  bound quantiles on real sinks: ", quant([r["bound"] for r in real]))
    for tau in sorted({t for r in R for t in r["rep"]}, key=float):
        rep = [r for r in det if r["rep"][tau]]
        un = [r for r in det if not r["rep"][tau]]
        tp = sum(r["truth_lo"] for r in rep)
        print(" tau=%s reported=%d recall=%.3f precision=%.3f | unreported=%d (real %d)"
              % (tau, len(rep), tp / max(1, len(real)), tp / max(1, len(rep)), len(un), sum(r["truth_lo"] for r in un)))
        for d in (0.01, 0.05, 0.1, 0.2):
            acc = [r for r in un if r["bound"] <= d]
            fa = sum(r["truth_lo"] for r in acc)
            print("    delta=%.2f accepted=%4d false-accepts=%3d FDR=%.3f power=%.3f"
                  % (d, len(acc), fa, fa / max(1, len(acc)), (len(acc) - fa) / max(1, len(clean))))
    src = collections.Counter(a["source"] for r in hole for a in r["cut"])
    print("  cut facts by label source:", dict(src))


def quant(xs):
    xs = sorted(xs)
    if not xs:
        return []
    return [round(xs[int(q * (len(xs) - 1))], 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)]


if __name__ == "__main__":
    main()
