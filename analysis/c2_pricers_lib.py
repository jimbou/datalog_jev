"""C2: how pricers price bundled-library methods (holes of the F1 step-e fallback) against framework methods.

Key: the rubric key's agreement part (Sonnet 5 and GPT 6.1 rubric labels agree; disagreements and U are left out, as
K2 is not available for library methods). Groups: framework methods of the main corpus (old hole file), new framework
methods and bundled-library methods of the F1-rescued apps. Per pricer and group: decided candidate flows, share real,
share of real flows priced <= 0.05 (the dangerous low prices), share of absent flows priced <= 0.05 (the useful ones),
and AUC (probability that a real flow gets a higher price than an absent one).
Usage: python3 analysis/c2_pricers_lib.py
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda f: os.path.join(ROOT, "data", f)
fw = {l.strip() for l in open(D("android_classes.txt"))}
old = {tuple(l.rstrip("\n").split("\t")[:2]) for l in open(D("rubric_methods.tsv"))}
new = {tuple(l.rstrip("\n").split("\t")) for l in open(D("f1/rubric_methods_f1.tsv"))}
lab = lambda n: {(d["cls"], d["sig"]): d["labels"] for d in map(json.loads, open(D("oracle-rubric-%s.jsonl" % n))) if "labels" in d}
S, G = lab("sonnet5"), lab("gpt61")
groups = {"framework, main corpus": old, "framework, rescued apps": {k for k in new if k[0] in fw},
          "bundled library, rescued apps": {k for k in new if k[0] not in fw}}


def auc(pos, neg):
    if not pos or not neg:
        return float("nan")
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank, r, i = 0.0, 1, 0
    while i < len(allv):  # average ranks for ties
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (r + r + (j - i) - 1) / 2
        rank += avg * sum(1 for t in allv[i:j] if t[1])
        r += j - i
        i = j
    return (rank - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


for tag in ["choice-obj", "sonnetp", "luna", "gflash"]:
    P = {(d["cls"], d["sig"]): d["p"] for d in map(json.loads, open(D("jev_holes_android_fw_%s_r0.jsonl" % tag))) if "p" in d}
    print("pricer", tag)
    for g, keys in groups.items():
        pos, neg = [], []
        for k in keys:
            if k not in S or k not in G or k not in P:
                continue
            for a, b, p in zip(S[k], G[k], P[k]):
                if a is None or b is None or a != b:
                    continue
                (pos if a else neg).append(p)
        n = len(pos) + len(neg)
        print("  %-30s decided %6d  real %4.1f%%  real priced<=0.05 %4.1f%%  absent priced<=0.05 %4.1f%%  AUC %.3f" % (
            g, n, 100 * len(pos) / max(1, n), 100 * sum(p <= 0.05 for p in pos) / max(1, len(pos)),
            100 * sum(p <= 0.05 for p in neg) / max(1, len(neg)), auc(pos, neg)))
