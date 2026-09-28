"""Evaluate stage: price the stored flow graphs and compute per-sink verdicts.

Usage: evaluate.py PRICING [APP_GLOB]      (env: JOBS)
  PRICING  a Jev wording with prices in data/jev_holes_android_fw_<PRICING>_r*.jsonl
           (taint, choice, choice-obj, ...), or a baseline:
             uniform  every candidate edge costs 1, so the bound is the size of the smallest
                      receipt (B4, Bastani-style counting; any flat price gives the same ranking)
             freq     frequency prior (B7): share of FlowDroid-modeled atoms with the same package
                      and endpoint kinds that are true, the method itself left out
           or a deletion-benchmark run (K1, no LLM in the answer key):
             k1-<RATE>-<SEED>-<PRICING>  truth = FlowDroid's models; a random RATE share of the
                      modeled methods (fixed by SEED) is deleted and becomes priced holes, the rest
                      become fixed code edges, unmodeled methods mean no flow (as in FlowDroid)
Reads data/graphs/*.npz (analysis/run_android.py), writes data/android_<PRICING>.jsonl with one
record per reachable sink site: truth_lo / truth_hi (answer key with unknown facts off / on),
rep (reported at each tau), bound (min cut, None if reachable through code alone) and the cut.
"""
import collections, glob, hashlib, json, math, os, sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order, maximum_flow

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_android import GRAPHS, ROOT, framework_holes

SCALE = 10000  # prices become integer capacities ceil(p * SCALE); rounding up keeps the bound valid
BIG = 1 << 28
TAUS = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
JOBS = int(os.environ.get("JOBS", "4"))


def labelled_holes():
    """Framework holes with answer-key labels: FlowDroid summaries plus Sonnet silver labels."""
    holes = framework_holes()
    oracle = os.path.join(ROOT, "data/oracle-sonnet5-unk.jsonl")
    if os.path.exists(oracle):
        for d in map(json.loads, open(oracle)):
            h = holes.get((d["cls"], d["sig"]))
            if h and h["source"] == "none":
                h["source"] = "silver"
                for a, l in zip(h["atoms"], d["labels"]):
                    a["label"] = l
    return holes


def jev_prices(wording):
    acc = collections.defaultdict(list)
    for p in glob.glob(os.path.join(ROOT, "data/jev_holes_android_fw_%s_r*.jsonl" % wording)):
        for d in map(json.loads, open(p)):
            acc[(d["cls"], d["sig"])].append(d["p"])
    if not acc:
        sys.exit("no prices for %r" % wording)
    return {k: [sum(x) / len(x) for x in zip(*v)] for k, v in acc.items()}


def freq_prices(holes):
    """B7: smoothed rate of true atoms among FlowDroid-modeled methods in the same package with
    the same endpoint kinds, leaving the method itself out; falls back to kinds alone."""
    def kind(e):
        return "arg" if e.startswith("arg") else e

    def pkg(cls):
        return ".".join(cls.split(".")[:2])

    by_pkg, by_kind = collections.Counter(), collections.Counter()
    tot_pkg, tot_kind = collections.Counter(), collections.Counter()
    modeled = [(k, h) for k, h in holes.items() if h["source"] in ("summary", "implicit-neg")]
    for (cls, sub), h in modeled:
        for a in h["atoms"]:
            kk = (kind(a["src"]), kind(a["tgt"]))
            tot_pkg[(pkg(cls), kk)] += 1
            by_pkg[(pkg(cls), kk)] += a["label"]
            tot_kind[kk] += 1
            by_kind[kk] += a["label"]
    prices = {}
    for (cls, sub), h in holes.items():
        own = h["source"] in ("summary", "implicit-neg")
        ps = []
        for a in h["atoms"]:
            kk = (kind(a["src"]), kind(a["tgt"]))
            t, n = by_pkg[(pkg(cls), kk)], tot_pkg[(pkg(cls), kk)]
            if own:  # leave the method's own atoms out of its prior
                same = [b for b in h["atoms"] if (kind(b["src"]), kind(b["tgt"])) == kk]
                t -= sum(b["label"] for b in same)
                n -= len(same)
            if n < 5:
                t, n = by_kind[kk], tot_kind[kk]
            ps.append((t + 1) / (n + 2))
        prices[(cls, sub)] = ps
    return prices


MODELED = ("summary", "implicit-neg")


def deleted(key, rate, seed):
    """Stable pseudo-random choice of the modeled methods removed in deletion run (rate, seed)."""
    h = hashlib.md5(("%s|%s|%s" % (seed, key[0], key[1])).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64 < rate


CTX = None


def evaluate(path):
    holes, prices, uniform, k1 = CTX
    app = os.path.basename(path)[:-4]
    g = np.load(path)
    N = int(g["n"]) + 1
    snk, src = N - 1, 0
    keys = list(zip(g["hole_cls"].tolist(), g["hole_sub"].tolist()))
    cu, cm, ch, ck = g["cand_u"], g["cand_mid"], g["cand_hole"], g["cand_k"]
    code_u, code_v = g["code_u"], g["code_v"]
    atoms = [holes.get(keys[h], {"atoms": []})["atoms"] for h in range(len(keys))]
    label = np.array([atoms[h][k]["label"] if k < len(atoms[h]) else None for h, k in zip(ch, ck)], dtype=object)
    if k1:
        rate, seed = k1
        modeled_h = np.array([holes.get(k, {}).get("source") in MODELED for k in keys], dtype=bool)
        deleted_h = modeled_h & np.array([deleted(k, rate, seed) for k in keys], dtype=bool)
        modeled, gone = modeled_h[ch], deleted_h[ch]
        fixed = modeled & ~gone & np.array([l is True for l in label], dtype=bool)
        code_u, code_v = np.concatenate([code_u, cu[fixed]]), np.concatenate([code_v, cm[fixed]])
        cu, cm, ch, ck, label = cu[gone], cm[gone], ch[gone], ck[gone], label[gone]
    if uniform:
        p = np.ones(len(cu))
        caps_c = np.ones(len(cu), dtype=np.int64)
    else:
        p = np.array([prices[keys[h]][k] for h, k in zip(ch, ck)], dtype=float)
        caps_c = np.maximum(1, np.ceil(p * SCALE)).astype(np.int64)
    us = np.concatenate([code_u, cu]).astype(np.int32)
    vs = np.concatenate([code_v, cm]).astype(np.int32)
    caps = np.concatenate([np.full(len(code_u), BIG, dtype=np.int64), caps_c])
    code = np.zeros(len(us), dtype=bool)
    code[:len(code_u)] = True
    is_cand = ~code

    def reach(allowed):
        m = code | allowed
        A = csr_matrix((np.ones(m.sum()), (us[m], vs[m])), shape=(N, N))
        r = np.zeros(N, dtype=bool)
        r[breadth_first_order(A, src, return_predecessors=False)] = True
        return r

    def on_cand(mask_c):
        return np.concatenate([np.zeros(len(code_u), dtype=bool), mask_c])

    lab_true = np.array([l is True for l in label], dtype=bool)
    lab_unk = np.array([l is None for l in label], dtype=bool)
    code_reach = reach(on_cand(np.zeros(len(cu), dtype=bool)))
    truth_lo, truth_hi = reach(on_cand(lab_true)), reach(on_cand(lab_true | lab_unk))
    rep = {} if uniform else {t: reach(on_cand(p >= t)) for t in TAUS}
    rev = csr_matrix((np.ones(len(us)), (vs, us)), shape=(N, N))
    ptr, nodes = g["sink_ptr"], g["sink_nodes"]
    recs = []
    for i, site in enumerate(g["sink_site"].tolist()):
        ns = nodes[ptr[i]:ptr[i + 1]]
        info = {"app": app, "site": site, "truth_lo": bool(truth_lo[ns].any()), "truth_hi": bool(truth_hi[ns].any()),
                "rep": {str(t): bool(r[ns].any()) for t, r in rep.items()}}
        if code_reach[ns].any():
            recs.append(dict(info, bound=None, cut=[]))
            continue
        keep = np.zeros(N, dtype=bool)
        for n in ns:
            keep[breadth_first_order(rev, n, directed=True, return_predecessors=False)] = True
        if not keep[src]:
            continue
        m = keep[us] & keep[vs]
        eu = np.concatenate([us[m], ns.astype(np.int32)])
        ev = np.concatenate([vs[m], np.full(len(ns), snk, dtype=np.int32)])
        ec = np.concatenate([caps[m], np.full(len(ns), BIG)])
        C = csr_matrix((ec.astype(np.int32), (eu, ev)), shape=(N, N))
        C.sum_duplicates()
        res = maximum_flow(C, src, snk)
        R = (C - res.flow).tocsr()
        R.data = (R.data > 0).astype(np.int8)
        R.eliminate_zeros()
        S = np.zeros(N, dtype=bool)
        S[breadth_first_order(R, src, directed=True, return_predecessors=False)] = True
        cut = []
        for j in np.nonzero(keep[cm] & S[cu] & ~S[cm])[0]:
            cls, sub = keys[ch[j]]
            a = atoms[ch[j]][ck[j]]
            cut.append({"cls": cls, "sub": sub, "k": int(ck[j]), "src": a["src"], "tgt": a["tgt"],
                        "label": a["label"], "source": holes[(cls, sub)]["source"], "p": float(p[j])})
        val = float(res.flow_value) if uniform else res.flow_value / SCALE
        recs.append(dict(info, bound=val, cut=cut))
    return app, recs


def main():
    pricing = sys.argv[1]
    app_glob = sys.argv[2] if len(sys.argv) > 2 else "*"
    k1 = None
    base = pricing
    if pricing.startswith("k1-"):
        _, rate, seed, base = pricing.split("-", 3)
        k1 = (float(rate), int(seed))
    holes = framework_holes() if k1 else labelled_holes()
    uniform = base == "uniform"
    prices = None if uniform else freq_prices(holes) if base == "freq" else jev_prices(base)
    global CTX
    CTX = (holes, prices, uniform, k1)
    paths = sorted(glob.glob(os.path.join(GRAPHS, app_glob + ".npz")))
    import multiprocessing
    with open(os.path.join(ROOT, "data/android_%s.jsonl" % pricing), "w") as f, \
            multiprocessing.get_context("fork").Pool(JOBS) as pool:
        for app, recs in pool.imap_unordered(evaluate, paths):
            for r in recs:
                f.write(json.dumps(r) + "\n")
            print(app, "sinks", len(recs), flush=True)


if __name__ == "__main__":
    main()
