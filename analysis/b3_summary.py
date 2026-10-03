"""Operating point of an LLM-as-fact baseline (B3) from an evaluation run priced with 1.0 / 0.0.

Usage: b3_summary.py RUN [RUN ...]     RUN is a pricing name such as b3 or k1-0.25-1-b3
A verdict is cleared when it is not reported at tau = 0.5 (no flow using the LLM's yes answers). On the hard
slice (verdicts that depend on holes), a wrong clearance is a cleared verdict whose truth is a real flow.
There is no guarantee to tune: the baseline has one operating point, so it is reported as it is, per app.
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def one(run):
    clean = cleared_clean = wrong = cleared = real = 0
    apps, wrong_apps = set(), set()
    for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % run)):
        r = json.loads(l)
        if r["bound"] is None or r["truth_lo"] != r["truth_hi"]:
            continue
        apps.add(r["app"])
        flag = r["rep"]["0.5"]
        if r["truth_lo"]:
            real += 1
        else:
            clean += 1
        if not flag:
            cleared += 1
            if r["truth_lo"]:
                wrong += 1
                wrong_apps.add(r["app"])
            else:
                cleared_clean += 1
    print("%-22s apps=%d clean=%d real=%d | cleared %d (%.1f%% of clean) | wrong clearances %d = %.1f%% of cleared, in %d of %d apps (%.1f%%)" % (
        run, len(apps), clean, real, cleared, 100 * cleared_clean / max(1, clean), wrong, 100 * wrong / max(1, cleared),
        len(wrong_apps), len(apps), 100 * len(wrong_apps) / max(1, len(apps))))


if __name__ == "__main__":
    for run in sys.argv[1:]:
        one(run)
