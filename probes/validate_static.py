"""Compare oracle 1 answers (data/oracle_static.jsonl) with FlowDroid's labels.

Usage: validate_static.py KEYS_TSV
The number that matters is "no-flow but FlowDroid says flow": that is the checker's error rate
on the answers used to clear verdicts.
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
holes = {(r["cls"], r["sig"]): r for r in map(json.loads, open(os.path.join(ROOT, "data/holes_android_fw.jsonl")))}
keys = {tuple(l.rstrip("\n").split("\t")) for l in open(sys.argv[1]) if l.strip()}
c, bad = collections.Counter(), []
for d in map(json.loads, open(os.path.join(ROOT, "data/oracle_static.jsonl"))):
    k = (d["cls"], d["sig"])
    if k not in keys or holes[k]["source"] not in ("summary", "implicit-neg"):
        continue
    for a, l in zip(holes[k]["atoms"], d["labels"]):
        c[(l, a["label"])] += 1
        if l == "no-flow" and a["label"] is True:
            bad.append("%s.%s %s>%s" % (k[0].split(".")[-1], k[1].split("(")[0].split(" ")[-1], a["src"], a["tgt"]))
for l in ("no-flow", "flow", "unknown"):
    t, f = c[(l, True)], c[(l, False)]
    print("%-8s %4d atoms: FlowDroid says flow %3d, no flow %3d" % (l, t + f, t, f))
n = c[("no-flow", True)] + c[("no-flow", False)]
print("error rate of no-flow answers: %d/%d = %.1f%%" % (c[("no-flow", True)], n, 100 * c[("no-flow", True)] / max(1, n)))
print("disagreements:", bad[:25])
