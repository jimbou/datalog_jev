"""Closing loop, step 1: rank holes by how many leaks FlowDroid would miss if they are real flows.

FlowDroid's world F = code edges + atoms its models mark as flows. A leak candidate is an atom
FlowDroid assumes absent (a modeled method without that flow, or a method it never modeled) whose
edge alone connects a source to a sink that F does not reach. For each such atom (method, atom k)
we count the sink sites and apps it would open, and rank by Jev price x sinks opened.

Usage: closing.py [PRICING] [TOP]
Writes data/leak_candidates.jsonl (all candidates, ranked).
"""
import collections, glob, json, os, sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import MODELED, jev_prices, labelled_holes
from run_android import GRAPHS, ROOT


DATA_TYPES = ("java.lang.String", "java.lang.CharSequence", "byte[]", "char[]", "java.lang.String[]",
              "android.net.Uri", "android.content.Intent", "android.os.Bundle", "android.content.ContentValues",
              "org.json.JSONObject", "org.json.JSONArray", "java.io.File", "java.net.URL", "java.net.URI",
              "java.util.List", "java.util.Map", "java.util.Set", "java.util.Collection", "java.util.ArrayList",
              "java.util.HashMap", "java.lang.StringBuilder", "java.lang.Object")


def endpoint_type(cls, sub, e):
    if e == "this":
        return cls
    if e == "ret":
        return sub.split(" ")[0]
    ps = sub[sub.index("(") + 1:-1].split(",")
    i = int(e[3:])
    return ps[i] if i < len(ps) else "?"


def carries_data(row):
    """A flow a reviewer would call a data leak: both ends are data-carrying types."""
    ts = [endpoint_type(row["cls"], row["sub"], row["src"]), endpoint_type(row["cls"], row["sub"], row["tgt"])]
    return all(t in DATA_TYPES for t in ts)


def reach_set(u, v, n, starts):
    A = csr_matrix((np.ones(len(u)), (u, v)), shape=(n, n))
    r = np.zeros(n, dtype=bool)
    for s in starts:
        if not r[s]:
            r[breadth_first_order(A, int(s), return_predecessors=False)] = True
    return r


def app_candidates(path, holes):
    """{(cls, sub, k): set of sink sites opened} for one app."""
    g = np.load(path)
    n = int(g["n"])
    keys = list(zip(g["hole_cls"].tolist(), g["hole_sub"].tolist()))
    cu, cm, ch, ck = g["cand_u"], g["cand_mid"], g["cand_hole"], g["cand_k"]
    src_ = [holes.get(k, {}).get("source") for k in keys]
    fd_true = np.array([src_[h] in MODELED and holes[keys[h]]["atoms"][k]["label"] is True
                        for h, k in zip(ch, ck)], dtype=bool)
    fu = np.concatenate([g["code_u"], cu[fd_true]])
    fv = np.concatenate([g["code_v"], cm[fd_true]])
    fwd = reach_set(fu, fv, n, [0])
    ptr, nodes, sites = g["sink_ptr"], g["sink_nodes"], g["sink_site"].tolist()
    absent = ~fd_true & fwd[cu]  # FlowDroid says no flow, and taint reaches its input in F
    out = collections.defaultdict(set)
    if not absent.any():
        return out
    for i, site in enumerate(sites):
        ns = nodes[ptr[i]:ptr[i + 1]]
        if fwd[ns].any():
            continue  # FlowDroid already reports this sink
        back = reach_set(fv, fu, n, ns)  # nodes that reach the sink in F (reversed edges)
        for j in np.nonzero(absent & back[cm])[0]:
            out[(keys[ch[j]][0], keys[ch[j]][1], int(ck[j]))].add(site)
    return out


def main():
    pricing = sys.argv[1] if len(sys.argv) > 1 else "choice-obj"
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    holes = labelled_holes()
    prices = jev_prices(pricing)
    sinks, apps = collections.defaultdict(int), collections.defaultdict(set)
    for path in sorted(glob.glob(os.path.join(GRAPHS, "*.npz"))):
        app = os.path.basename(path)[:-4]
        for key, sites in app_candidates(path, holes).items():
            sinks[key] += len(sites)
            apps[key].add(app)
    rows = []
    for (cls, sub, k), s in sinks.items():
        h = holes[(cls, sub)]
        a = h["atoms"][k]
        p = prices[(cls, sub)][k]
        rows.append({"cls": cls, "sub": sub, "k": k, "src": a["src"], "tgt": a["tgt"], "source": h["source"],
                     "key_label": a["label"], "p": p, "sinks": s, "apps": len(apps[(cls, sub, k)]),
                     "expected": p * len(apps[(cls, sub, k)])})
        rows[-1]["data"] = carries_data(rows[-1])
    rows.sort(key=lambda r: -r["expected"])
    with open(os.path.join(ROOT, "data/leak_candidates.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("%d leak-candidate atoms; %d open >= 1 sink in >= 2 apps" % (len(rows), sum(r["apps"] >= 2 for r in rows)))
    print("by FlowDroid status:", dict(collections.Counter(r["source"] for r in rows)))
    print("data-carrying:", sum(r["data"] for r in rows))
    for r in rows[:top]:
        print("%5.2f  p=%.2f apps=%3d sinks=%4d  %-9s key=%-5s %s.%s %s>%s" % (
            r["expected"], r["p"], r["apps"], r["sinks"], r["source"], r["key_label"],
            r["cls"].split(".")[-1], r["sub"].split("(")[0].split(" ")[-1], r["src"], r["tgt"]))


if __name__ == "__main__":
    main()
