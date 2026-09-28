"""Apply oracle 1 results to Jev prices: every atom the static checker proves no-flow gets price EPS.

Usage: reprice_o1.py BASE_PRICING OUT_PRICING [EPS] [KEYS_TSV]
Reads data/jev_holes_android_fw_<BASE>_r0.jsonl and data/oracle_static.jsonl (restricted to KEYS_TSV
if given), writes data/jev_holes_android_fw_<OUT>_r0.jsonl, and reports how the no-flow answers
compare with the answer key (FlowDroid plus Sonnet silver labels).
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from evaluate import labelled_holes


def main():
    base, out = sys.argv[1], sys.argv[2]
    eps = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
    keys = {tuple(l.rstrip("\n").split("\t")) for l in open(sys.argv[4])} if len(sys.argv) > 4 else None
    holes = labelled_holes()
    no_flow, agree = set(), collections.Counter()
    for d in map(json.loads, open(os.path.join(ROOT, "data/oracle_static.jsonl"))):
        k = (d["cls"], d["sig"])
        if (keys and k not in keys) or k not in holes:
            continue
        for i, (a, l) in enumerate(zip(holes[k]["atoms"], d["labels"])):
            if l == "no-flow":
                no_flow.add((k, i))
                agree[(holes[k]["source"], a["label"])] += 1
    print("no-flow atoms by (key source, key label):", dict(agree))
    n = 0
    with open(os.path.join(ROOT, "data/jev_holes_android_fw_%s_r0.jsonl" % out), "w") as f:
        for d in map(json.loads, open(os.path.join(ROOT, "data/jev_holes_android_fw_%s_r0.jsonl" % base))):
            k = (d["cls"], d["sig"])
            p = [min(x, eps) if (k, i) in no_flow else x for i, x in enumerate(d["p"])]
            n += sum(1 for i in range(len(p)) if (k, i) in no_flow)
            f.write(json.dumps(dict(d, p=p)) + "\n")
    print("atoms repriced to %.3f: %d" % (eps, n))


if __name__ == "__main__":
    main()
