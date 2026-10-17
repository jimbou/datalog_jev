"""F1: score the rescued apps (data/android_fm-rk-<pricer>_f1[e_fb].jsonl) with the threshold certified on all main apps.
Usage (on the server): f1_score.py APP1,APP2,...   (apps to drop from the fallback set, e.g. the 17 with R8-moved app code)
PRICERS=a,b,... picks the pricers (default choice-obj,sonnetp,b6,freq,uniform).
"""
import collections, json, os, sys
sys.path.insert(0, os.path.expanduser("~/receipts/analysis"))
from app_ltt import calibrate, loss, DELTAS
os.chdir(os.path.expanduser("~/receipts/data"))
mis = set(sys.argv[1].split(","))
def load(p, suffix, skip=()):
    by, und, tot = collections.defaultdict(list), 0, 0
    for r in map(json.loads, open("android_fm-rk-%s%s.jsonl" % (p, suffix))):
        if r["app"] in skip or r["bound"] is None: continue
        tot += 1
        if r["truth_lo"] != r["truth_hi"]: und += 1; continue
        by[r["app"]].append((r["bound"], r["truth_lo"]))
    return by, und, tot
for alpha in (0.05, 0.1):
    print("alpha", alpha)
    for p in os.environ.get("PRICERS", "choice-obj,sonnetp,b6,freq,uniform").split(","):
        main, _, _ = load(p, "")
        deltas = [0.5, 1, 2, 3, 4, 5] if p == "uniform" else DELTAS
        d = calibrate(sorted(main), main, alpha, 0.1, deltas)
        row = []
        for suf, skip in [("", ()), ("_f1", ()), ("_f1e_fb", ()), ("_f1e_fb", mis)]:
            by, und, tot = load(p, suf, skip)
            clean = sum(not r for v in by.values() for _, r in v)
            acc = sum(1 for v in by.values() for b, r in v if b <= d and not r) if d is not None else 0
            fa = sum(loss(by[a], d) for a in by) if d is not None else 0
            row.append("%5.1f%% %d/%d" % (100 * acc / max(1, clean), fa, len(by)))
        print("  %-10s delta %-5s | main %-14s | retry %-12s | fallback %-12s | fallback-17 %s" % (p, d, *row))
