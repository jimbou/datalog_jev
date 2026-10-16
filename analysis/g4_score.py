"""G4: score the IzzyOnDroid apps (data/android_fm-rk-<pricer>_izzy[_fb].jsonl) with the threshold certified on all
307 main F-Droid apps, unchanged (as analysis/f1_score.py for the F1-rescued apps).
For each pricer and alpha: certified threshold, then per set (main, IzzyOnDroid full builds, fallback builds, both):
share of the hard slice cleared, apps with a wrong clearance / apps with a decided verdict, verdicts left undecided by
the key.
"""
import collections, json, os, sys
sys.path.insert(0, os.path.expanduser("~/receipts/analysis"))
from app_ltt import calibrate, loss, DELTAS
os.chdir(os.path.expanduser("~/receipts/data"))


def load(p, suffixes):
    by, und = collections.defaultdict(list), 0
    for suf in suffixes:
        for r in map(json.loads, open("android_fm-rk-%s%s.jsonl" % (p, suf))):
            if r["bound"] is None:
                continue
            if r["truth_lo"] != r["truth_hi"]:
                und += 1
                continue
            by[r["app"] + suf].append((r["bound"], r["truth_lo"]))
    return by, und


for alpha in (0.05, 0.1):
    print("alpha", alpha)
    for p in ["choice-obj", "sonnetp", "sonnet55def3", "b6", "freq", "uniform"]:
        main, _ = load(p, [""])
        deltas = [0.5, 1, 2, 3, 4, 5] if p == "uniform" else DELTAS
        d = calibrate(sorted(main), main, alpha, 0.1, deltas)
        row = []
        for sufs in [[""], ["_izzy"], ["_izzy_fb"], ["_izzy", "_izzy_fb"]]:
            by, und = load(p, sufs)
            clean = sum(not r for v in by.values() for _, r in v)
            acc = sum(1 for v in by.values() for b, r in v if b <= d and not r) if d is not None else 0
            fa = sum(loss(by[a], d) for a in by) if d is not None else 0
            row.append("%5.1f%% %d/%d (und %d)" % (100 * acc / max(1, clean), fa, len(by), und))
        print("  %-12s delta %-5s | main %s | izzy full %s | izzy fallback %s | izzy all %s" % (p, d, *row))
