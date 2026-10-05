"""Evaluate stage: price the stored flow graphs and compute per-sink verdicts.

Usage: evaluate.py PRICING [APP_GLOB]      (env: JOBS, GRAPHS_DIR for another graph folder, OUT_SUFFIX for another output name)
  PRICING  a Jev wording with prices in data/jev_holes_android_fw_<PRICING>_r*.jsonl
           (taint, choice, choice-obj, ...), or a baseline:
             uniform  every candidate edge costs 1, so the bound is the size of the smallest
                      receipt (B4, Bastani-style counting; any flat price gives the same ranking)
             freq     frequency prior (B7): share of FlowDroid-modeled atoms with the same package
                      and endpoint kinds that are true, the method itself left out
             b3       IRIS-style (B3): Sonnet 5's yes/no per candidate flow taken as fact (price 1 or 0, no
                      uncertainty); read the verdict from rep["0.5"] with analysis/b3_summary.py
             b6       feature classifier (B6): logistic regression on signature features (name tokens,
                      package, types, flow kind) trained on FlowDroid-modeled atoms; each method is priced
                      by a model that never saw it (5 folds by method)
           or a deletion-benchmark run (K1, no LLM in the answer key):
             k1-<RATE>-<SEED>-<PRICING>  truth = FlowDroid's models; a random RATE share of the
                      modeled methods (fixed by SEED) is deleted and becomes priced holes, the rest
                      become fixed code edges, unmodeled methods mean no flow (as in FlowDroid)
           or a pricing under another answer key (truth only; prices and training data stay the same):
             k2-<PRICING>   K2: StubDroid summaries generated from the Android 13 implementation (data/k2_labels.json,
                            probes/k2_labels_all.py); unknown flows leave a verdict undetermined (excluded)
             k2s-<PRICING>  K2, strict reading of "no" (class logs without exceptions)
             au-<PRICING>   the main key with the audit's answers (data/audit_override.json) on the receipt facts
             ah-<PRICING>   the same with the person's source check on 27 facts (data/audit_override_human.json)
             ah2-<PRICING>  and with the second human check, 40 facts the AI called no (data/audit_override_human2.json)
Reads data/graphs/*.npz (analysis/run_android.py), writes data/android_<PRICING>.jsonl with one
record per reachable sink site: truth_lo / truth_hi (answer key with unknown facts off / on),
rep (reported at each tau), bound (min cut, None if reachable through code alone) and the cut.
"""
import collections, glob, hashlib, json, math, os, re, sys, zlib
import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order, connected_components, maximum_flow

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


def key_holes(key):
    """Holes with the labels of an answer key: k3 (default: FlowDroid plus Sonnet), k2 / k2s (StubDroid on the
    real code), au (k3 with the audit's answers on the receipt facts)."""
    if key == "k3":
        return labelled_holes()
    if key in ("k2", "k2s"):
        holes = framework_holes()
        lab = json.load(open(os.path.join(ROOT, "data/k2_labels.json")))
        for (cls, sub), h in holes.items():
            e = lab.get(cls + "\t" + sub)
            for i, a in enumerate(h["atoms"]):
                a["label"] = e["lenient" if key == "k2" else "strict"][i] if e else None
            h["source"] = key
        return holes
    holes = labelled_holes()
    ov = json.load(open(os.path.join(ROOT, {"ah": "data/audit_override_human.json", "ah2": "data/audit_override_human2.json"}.get(key, "data/audit_override.json"))))
    for (cls, sub), h in holes.items():
        for a in h["atoms"]:
            k = "\t".join((cls, sub, a["src"], a["tgt"]))
            if k in ov:
                a["label"] = ov[k]
                h["source"] = "audit"
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
PRIMS = {"int", "long", "short", "byte", "boolean", "char", "float", "double", "void"}


def b6_features(cls, sig, a):
    """Signature features of one candidate flow, as strings (no labels, no LLM)."""
    ret = sig.split(" ", 1)[0]
    name = sig[sig.index(" ") + 1:sig.index("(")]
    ps = sig[sig.index("(") + 1:-1]
    params = ps.split(",") if ps else []

    def typ(e):
        return cls if e == "this" else ret if e == "ret" else params[int(e[3:])] if int(e[3:]) < len(params) else "?"

    def knd(e):
        return "arg" if e.startswith("arg") else e

    s, t = a["src"], a["tgt"]
    ts, tt = typ(s), typ(t)
    toks = [x.lower() for x in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", name)] or [name]
    flow = "%s>%s" % (knd(s), knd(t))
    pkg3 = ".".join(cls.split(".")[:3])
    f = ["bias", "flow=" + flow, "name=" + name, "prefix=" + toks[0], "cls=" + cls, "pkg2=" + ".".join(cls.split(".")[:2]),
         "pkg3=" + pkg3, "srcT=" + ts, "tgtT=" + tt, "T=%s>%s" % (ts, tt), "ret=" + ret, "nparams=%d" % len(params),
         "srcidx=" + s, "tgtidx=" + t, "prefix|flow=%s|%s" % (toks[0], flow), "flow|tgtT=%s|%s" % (flow, tt),
         "flow|srcT=%s|%s" % (flow, ts), "name|flow=%s|%s" % (name, flow), "cls|flow=%s|%s" % (cls, flow),
         "pkg3|flow=%s|%s" % (pkg3, flow), "prefix|srcT|tgtT=%s|%s|%s" % (toks[0], ts, tt)]
    f += ["tok=" + x for x in toks]
    f += ["tok|flow=%s|%s" % (x, flow) for x in toks]
    if ts == tt:
        f.append("same_type")
    if ts in PRIMS:
        f.append("src_prim")
    if tt in PRIMS:
        f.append("tgt_prim")
    return f


def b6_prices(holes, dim=1 << 16, lam=1.0, folds=5, exclude=None, fold_by="method", extra=None):
    """B6: logistic regression on signature features, trained on FlowDroid-modeled atoms with labels,
    cross-fitted by method (a method is priced by a model that did not see it). exclude(key) removes
    methods from training (deletion benchmark: deleted models are unknown to the pricer too). fold_by="class"
    keeps all methods of a class in one fold; extra maps (cls, sub) to one more per-atom score (for example a Jev
    price) that is added as a feature in logit form."""
    keys, rows, fold_of = [], [], []
    for (cls, sub), h in holes.items():
        fo = int.from_bytes(hashlib.md5(((cls if fold_by == "class" else "%s|%s" % (cls, sub))).encode()).digest()[:8], "big") % folds
        for k, a in enumerate(h["atoms"]):
            keys.append((cls, sub, k, h["source"] in MODELED and a["label"] is not None and not (exclude and exclude((cls, sub))),
                         bool(a["label"])))
            fold_of.append(fo)
            cols = sorted({zlib.crc32(x.encode()) % dim for x in b6_features(cls, sub, a)})
            rows.append(cols)
    n = len(rows)
    indptr = np.zeros(n + 1, dtype=np.int64)
    indptr[1:] = np.cumsum([len(r) for r in rows])
    X = csr_matrix((np.ones(indptr[-1]), np.concatenate([np.array(r, dtype=np.int64) for r in rows]), indptr), shape=(n, dim))
    if extra is not None:
        from scipy.sparse import hstack
        ev = np.array([min(max(extra[(c, sb)][k], 1e-3), 1 - 1e-3) for c, sb, k, _, _ in keys])
        X = hstack([X, csr_matrix((np.log(ev / (1 - ev)) / 3.0).reshape(-1, 1))], format="csr")
        dim += 1
    train = np.array([k[3] for k in keys])
    y = np.array([k[4] for k in keys], dtype=float)
    fold_of = np.array(fold_of)
    pred = np.zeros(n)
    for f in range(folds):
        tr = train & (fold_of != f)
        Xt, yt = X[tr], y[tr]

        def fun(w):
            pz = 1 / (1 + np.exp(-(Xt @ w)))
            loss = -(yt * np.log(pz + 1e-12) + (1 - yt) * np.log(1 - pz + 1e-12)).sum() + 0.5 * lam * (w @ w)
            return loss, Xt.T @ (pz - yt) + lam * w

        w = minimize(fun, np.zeros(dim), jac=True, method="L-BFGS-B", options={"maxiter": 200}).x
        te = fold_of == f
        pred[te] = 1 / (1 + np.exp(-(X[te] @ w)))
    prices = {}
    for (cls, sub, k, _, _), pz in zip(keys, np.clip(pred, 0.005, 0.995)):
        prices.setdefault((cls, sub), []).append(float(pz))
    return prices



def b3_prices(holes):
    """B3: an LLM's yes/no per candidate flow taken as fact (price 1.0 or 0.0). Labels come from
    data/oracle-sonnet5-{unk,mod,val}.jsonl; a method nobody labeled gets 0.0 (no flow, as in FlowDroid)."""
    lab = {}
    for name in ("unk", "mod", "val"):
        path = os.path.join(ROOT, "data/oracle-sonnet5-%s.jsonl" % name)
        if os.path.exists(path):
            for d in map(json.loads, open(path)):
                if "labels" in d:
                    lab[(d["cls"], d["sig"])] = d["labels"]
    return {k: [1.0 if (k in lab and i < len(lab[k]) and lab[k][i]) else 0.0 for i in range(len(h["atoms"]))]
            for k, h in holes.items()}


def b6_variant(name, holes, k1):
    """b6 = signature classifier; c = folds by class; j = Jev price (choice-obj) as an extra feature."""
    excl = (lambda key: deleted(key, *k1)) if k1 else None
    return b6_prices(holes, exclude=excl, fold_by="class" if "c" in name[2:] else "method",
                     extra=jev_prices("choice-obj") if "j" in name[2:] else None)


def deleted(key, rate, seed, by_class=False):
    """Stable pseudo-random choice of the modeled methods removed in deletion run (rate, seed); with by_class
    a class is removed with all its methods, so no sibling method of a deleted one stays modeled."""
    h = hashlib.md5(("%s|%s|%s" % (seed, key[0], "" if by_class else key[1])).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64 < rate


CTX = None
VERIFIED = set()
if os.environ.get("VERIFY_FILE"):  # list of [cls, sub, atom index] whose truth (in the tested key) a checker has established
    VERIFIED = {(c, sub, int(k)) for c, sub, k in json.load(open(os.environ["VERIFY_FILE"]))}


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
        rate, seed = k1[:2]
        by_class = len(k1) > 2 and k1[2]
        modeled_h = np.array([holes.get(k, {}).get("source") in MODELED for k in keys], dtype=bool)
        deleted_h = modeled_h & np.array([deleted(k, rate, seed, by_class) for k in keys], dtype=bool)
        modeled, gone = modeled_h[ch], deleted_h[ch]
        fixed = modeled & ~gone & np.array([l is True for l in label], dtype=bool)
        code_u, code_v = np.concatenate([code_u, cu[fixed]]), np.concatenate([code_v, cm[fixed]])
        cu, cm, ch, ck, label = cu[gone], cm[gone], ch[gone], ck[gone], label[gone]
    if VERIFIED:  # facts a checker has verified: a "no" removes the candidate, a "yes" becomes a code edge (see verify_select.py)
        vk = np.array([(keys[h][0], keys[h][1], int(k)) in VERIFIED for h, k in zip(ch, ck)], dtype=bool)
        vyes = vk & np.array([l is True for l in label], dtype=bool)
        vdone = vk & np.array([l is not None for l in label], dtype=bool)  # a fact the key cannot decide stays a hole
        code_u, code_v = np.concatenate([code_u, cu[vyes]]), np.concatenate([code_v, cm[vyes]])
        cu, cm, ch, ck, label = cu[~vdone], cm[~vdone], ch[~vdone], ck[~vdone], label[~vdone]
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
    # Exact speed-up: code edges have infinite capacity, so a finite cut never separates the nodes of a
    # strongly connected group of them. Contract each group once per app; bounds and cuts are unchanged.
    ncode = len(code_u)
    nc, lab = connected_components(csr_matrix((np.ones(ncode, dtype=np.int8), (us[:ncode], vs[:ncode])), shape=(N, N)),
                                   directed=True, connection="strong")
    lab = lab.astype(np.int32)
    a_, b_ = lab[us[:ncode]], lab[vs[:ncode]]
    differ = a_ != b_
    code_pairs = np.unique(a_[differ].astype(np.int64) * nc + b_[differ])
    ccu, ccm = lab[cu], lab[cm]  # candidate edges in contracted space
    T = nc
    cu_pair = (code_pairs // nc).astype(np.int32)
    cv_pair = (code_pairs % nc).astype(np.int32)
    ptr, nodes = g["sink_ptr"], g["sink_nodes"]
    sink_comps = np.unique(lab[nodes])
    # one preallocated zero-capacity edge from every sink-holding group to the super sink T; a sink turns its own on
    eu = np.concatenate([cu_pair, ccu, sink_comps]).astype(np.int32)
    ev = np.concatenate([cv_pair, ccm, np.full(len(sink_comps), T)]).astype(np.int32)
    ec = np.concatenate([np.full(len(cu_pair), BIG, dtype=np.int64), caps_c, np.zeros(len(sink_comps), dtype=np.int64)])
    ok = eu != ev
    C0 = csr_matrix((ec[ok].astype(np.int32), (eu[ok], ev[ok])), shape=(nc + 1, nc + 1))
    C0.sum_duplicates()
    pos = C0.indptr[sink_comps + 1] - 1  # column T is the largest, so it is last in its row
    assert (C0.indices[pos] == T).all()
    pos_of = np.full(nc + 1, -1, dtype=np.int64)
    pos_of[sink_comps] = pos
    n_real = ok & (ev != T)
    revc = csr_matrix((np.ones(int(n_real.sum()), dtype=np.int8), (ev[n_real], eu[n_real])), shape=(nc + 1, nc + 1))
    anyreach = reach(on_cand(np.ones(len(cu), dtype=bool)))
    src_c = int(lab[src])
    recs = []
    for i, site in enumerate(g["sink_site"].tolist()):
        ns = nodes[ptr[i]:ptr[i + 1]]
        info = {"app": app, "site": site, "truth_lo": bool(truth_lo[ns].any()), "truth_hi": bool(truth_hi[ns].any()),
                "rep": {str(t): bool(r[ns].any()) for t, r in rep.items()}}
        if code_reach[ns].any():
            recs.append(dict(info, bound=None, cut=[]))
            continue
        if not anyreach[ns].any():
            continue
        nsc = np.unique(lab[ns])
        keep = np.zeros(nc + 1, dtype=bool)
        for n in nsc:
            if not keep[n]:
                keep[breadth_first_order(revc, n, directed=True, return_predecessors=False)] = True
        data = C0.data.copy()
        data[pos_of[nsc]] = BIG
        C = csr_matrix((data, C0.indices, C0.indptr), shape=C0.shape)
        res = maximum_flow(C, src_c, T)
        R = (C - res.flow).tocsr()
        R.data = (R.data > 0).astype(np.int8)
        R.eliminate_zeros()
        S = np.zeros(nc + 1, dtype=bool)
        S[breadth_first_order(R, src_c, directed=True, return_predecessors=False)] = True
        cut = []
        for j in np.nonzero(keep[ccm] & S[ccu] & ~S[ccm])[0]:
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
    key = "k3"
    for pre, kname in (("k2s-", "k2s"), ("k2-", "k2"), ("au-", "au"), ("ah2-", "ah2"), ("ah-", "ah")):
        if pricing.startswith(pre):
            key, base = kname, pricing[len(pre):]
    if pricing.startswith("k1-") or pricing.startswith("k1c-"):
        tag, rate, seed, base = pricing.split("-", 3)
        k1 = (float(rate), int(seed), tag == "k1c")
    price_holes = framework_holes() if k1 else labelled_holes()  # prices and training data never use the tested key
    holes = price_holes if key == "k3" else key_holes(key)
    uniform = base == "uniform"
    prices = None if uniform else freq_prices(price_holes) if base == "freq" else b3_prices(price_holes) if base == "b3" else b6_variant(base, price_holes, k1) if base in ("b6", "b6c", "b6j", "b6jc") else jev_prices(base)
    if prices is not None:  # a pricer that left some methods unpriced: they get the uninformative 0.5 (costs power, not validity)
        miss = [k for k, h in price_holes.items() if k not in prices or len(prices[k]) != len(h["atoms"])]
        for k in miss:
            prices[k] = [0.5] * len(price_holes[k]["atoms"])
        if miss:
            print("WARNING: %d methods have no price from %r and were priced 0.5" % (len(miss), base), file=sys.stderr, flush=True)
    global CTX
    CTX = (holes, prices, uniform, k1)
    paths = sorted(glob.glob(os.path.join(GRAPHS, app_glob + ".npz")))
    import multiprocessing
    with open(os.path.join(ROOT, "data/android_%s%s.jsonl" % (pricing, os.environ.get("OUT_SUFFIX", ""))), "w") as f, \
            multiprocessing.get_context("fork").Pool(JOBS) as pool:
        for app, recs in pool.imap_unordered(evaluate, paths):
            for r in recs:
                f.write(json.dumps(r) + "\n")
            print(app, "sinks", len(recs), flush=True)


if __name__ == "__main__":
    main()
