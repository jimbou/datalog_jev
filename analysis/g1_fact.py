"""G1: a language model's answers taken as library models (the IRIS / SemTaint baseline) on the main key.

python3 analysis/g1_fact.py prices
    writes price files with 1.0 (flow) / 0.0 (no flow), so that a verdict is cleared exactly when every fact on its
    receipt is answered "no":
      jevfact   Jev's main price (choice-obj) >= 0.5
      gptfact   GPT-6.1's rubric labels (data/oracle-rubric-gpt61.jsonl); "undecidable" = no model = no flow,
                as FlowDroid treats a method without a model; methods without a label also 0
      gptfactu  the same, but "undecidable" = flow (sensitivity)
    Sonnet's labels are part of the main key, so they are not used here.
python3 analysis/g1_fact.py summary RUN [RUN ...]     (RUN e.g. fm-rk-jevfact)
    the single operating point, on all apps and on the held-out halves of 200 random app splits (seed 0, as
    app_ltt.py): share of the hard slice cleared, share of apps with a wrong clearance (mean and 95th percentile).
"""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")


def write(tag, rows):
    with open(os.path.join(D, "jev_holes_android_fw_%s_r0.jsonl" % tag), "w") as f:
        for cls, sig, p in rows:
            f.write(json.dumps({"cls": cls, "sig": sig, "p": p}) + "\n")
    print(tag, len(rows), "methods")


def prices():
    jev = [json.loads(l) for l in open(os.path.join(D, "jev_holes_android_fw_choice-obj_r0.jsonl"))]
    write("jevfact", [(r["cls"], r["sig"], [1.0 if x >= 0.5 else 0.0 for x in r["p"]]) for r in jev if r.get("p")])
    gpt = [json.loads(l) for l in open(os.path.join(D, "oracle-rubric-gpt61.jsonl"))]
    gpt = [d for d in gpt if "labels" in d]
    write("gptfact", [(d["cls"], d["sig"], [1.0 if x else 0.0 for x in d["labels"]]) for d in gpt])
    write("gptfactu", [(d["cls"], d["sig"], [0.0 if x is False else 1.0 for x in d["labels"]]) for d in gpt])


def summary(run, splits=200):
    per = {}  # app -> [hard-slice sinks, of them cleared, wrong clearances]
    for l in open(os.path.join(D, "android_%s.jsonl" % run)):
        r = json.loads(l)
        if r["bound"] is None or r["truth_lo"] != r["truth_hi"]:
            continue
        c = per.setdefault(r["app"], [0, 0, 0])
        cleared = not r["rep"]["0.5"]
        if r["truth_lo"]:
            c[2] += cleared
        else:
            c[0] += 1
            c[1] += cleared

    def stats(apps):
        hard = sum(per[a][0] for a in apps)
        return 100 * sum(per[a][1] for a in apps) / max(1, hard), 100 * sum(per[a][2] > 0 for a in apps) / len(apps)

    apps = sorted(per)
    cl, wr = stats(apps)
    rng = random.Random(0)
    held = []
    for _ in range(splits):
        s = apps[:]
        rng.shuffle(s)
        held.append(stats(s[len(s) // 2:]))
    w = sorted(h[1] for h in held)
    print("%-20s all %d apps: cleared %.1f%%, apps wrong %.1f%% | held-out halves (%d): cleared %.1f%%, apps wrong mean %.1f%% p95 %.1f%%, above 5%% in %d"
          % (run, len(apps), cl, wr, splits, sum(h[0] for h in held) / splits, sum(w) / splits, w[int(0.95 * splits) - 1],
             sum(x > 5 for x in w)))


if __name__ == "__main__":
    if sys.argv[1] == "prices":
        prices()
    else:
        for run in sys.argv[2:]:
            summary(run)
