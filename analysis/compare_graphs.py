"""Compare flow graphs of the same apps in two or three folders (F1 c: interpreted vs compiled Soufflé, and the paper's).

Usage: python3 analysis/compare_graphs.py DIR_A DIR_B [DIR_C]

Node numbers depend on the order in which Soufflé writes rows, so the comparison uses summaries that do not depend on
them: node, edge and candidate counts, the hole methods, the multiset of (hole, atom) over candidate edges, the sink
sites with their number of nodes, and Soufflé's statistics. The decisive check is that analysis/evaluate.py gives the
same per-sink results on both folders (bench/queues/f1_check.sh does both).
"""
import json
import os
import sys

import numpy as np


def canon(p):
    z = np.load(p)
    holes = [(c, s) for c, s in zip(z["hole_cls"].tolist(), z["hole_sub"].tolist())]
    sites = z["sink_site"].tolist()
    ptr = z["sink_ptr"]
    sink_nodes = z["sink_nodes"]
    return {
        "n": int(z["n"]),
        "code": len(z["code_u"]),
        "cand": len(z["cand_u"]),
        "holes": sorted(holes),
        "cand_holes": sorted((holes[h], int(k)) for h, k in zip(z["cand_hole"].tolist(), z["cand_k"].tolist())),
        "sinks": sorted((s, int(ptr[i + 1] - ptr[i])) for i, s in enumerate(sites)),
        "n_sink_calls": int(z["n_sink_calls"]),
        "stats": json.loads(str(z["stats"])),
    }


def main():
    dirs = sys.argv[1:]
    apps = sorted(set.intersection(*[{f[:-4] for f in os.listdir(d) if f.endswith(".npz")} for d in dirs]))
    print("apps in all of %s: %d" % (", ".join(dirs), len(apps)))
    for a in apps:
        cs = [canon(os.path.join(d, a + ".npz")) for d in dirs]
        same = [all(cs[0][k] == c[k] for k in cs[0]) for c in cs[1:]]
        diff = {k for c in cs[1:] for k in cs[0] if cs[0][k] != c[k]}
        print("%-40s %s%s" % (a, " ".join("same" if s else "DIFF" for s in same), (" (" + ",".join(sorted(diff)) + ")") if diff else ""))


if __name__ == "__main__":
    main()
