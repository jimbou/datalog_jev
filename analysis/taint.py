"""Per-test taint analysis over Soot facts with priced library holes.

For each OWASP Benchmark test in a taint category, builds a flow graph whose code
edges are fixed and whose JDK library-flow atoms are candidate edges (one cuttable
instance per call site), then reports:
  truth    - SRC reaches SNK using code edges + candidates true under FlowDroid summaries
  unsound  - reaches with code edges only (holes ignored)
  bound    - min cut SRC->SNK with candidate capacity = price (valid by union bound)
Output: data/tests_<pricing>.jsonl
"""
import collections, csv, json, os, sys
import networkx as nx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAINT_CATS = {"cmdi", "pathtraver", "sqli", "xss", "ldapi", "xpathi", "trustbound"}
APP = "org.owasp.benchmark"
SOURCE_CLASSES = {"javax.servlet.http.HttpServletRequest", "javax.servlet.ServletRequest",
                  "javax.servlet.http.HttpServletRequestWrapper", "javax.servlet.ServletRequestWrapper"}
SOURCE_RET = {"java.lang.String", "java.lang.String[]", "java.util.Enumeration", "java.util.Map",
              "javax.servlet.http.Cookie[]", "java.lang.StringBuffer", "java.io.BufferedReader",
              "javax.servlet.ServletInputStream", "java.io.Reader"}
SANITIZERS = ("org.owasp.esapi.Encoder", "org.springframework.web.util.HtmlUtils",
              "org.apache.commons.lang.StringEscapeUtils", "org.apache.commons.text.StringEscapeUtils")
FILE_CTORS = {"java.io.File", "java.io.FileInputStream", "java.io.FileOutputStream", "java.io.FileReader",
              "java.io.FileWriter", "java.io.RandomAccessFile"}


def is_sink(cat, cls, sub):
    name = sub[sub.index(" ") + 1:sub.index("(")]
    if cat == "cmdi":
        return (cls == "java.lang.Runtime" and name == "exec") or \
               (cls == "java.lang.ProcessBuilder" and name in ("<init>", "command"))
    if cat == "sqli":
        return cls.startswith(("java.sql.", "org.springframework.jdbc.", "org.hibernate.", "javax.persistence.")) \
            and name.startswith(("execute", "query", "prepare", "update", "batchUpdate", "addBatch",
                                 "createQuery", "createSQLQuery", "createNativeQuery", "nativeSQL"))
    if cat == "pathtraver":
        return (cls in FILE_CTORS and name == "<init>") or (cls == "java.nio.file.Paths" and name == "get") \
            or (cls == "java.nio.file.Files" and name.startswith("new"))
    if cat == "xss":
        return cls in ("java.io.PrintWriter", "javax.servlet.ServletOutputStream") and \
            name in ("print", "println", "write", "format", "printf", "append")
    if cat == "ldapi":
        return cls.startswith("javax.naming.") and name in ("search", "lookup")
    if cat == "xpathi":
        return cls.startswith("javax.xml.xpath.") and name in ("evaluate", "compile")
    if cat == "trustbound":
        return cls in ("javax.servlet.http.HttpSession",) and name in ("setAttribute", "putValue")
    return False


def load(rel):
    path = os.path.join(ROOT, "facts", rel + ".facts")
    return [l.rstrip("\n").split("\t") for l in open(path)] if os.path.exists(path) else []


def meth(var):
    return var[:var.rindex(">/") + 1]


class Program:
    def __init__(self):
        self.by_m = collections.defaultdict(lambda: collections.defaultdict(list))
        for rel in ("Alloc", "Move", "Load", "Store", "SLoad", "SStore"):
            for row in load(rel):
                v = row[0] if rel != "SStore" else row[1]
                self.by_m[meth(v)][rel].append(row)
        self.calls = collections.defaultdict(list)
        for site, m, kind, cls, sub, base, ret in load("Call"):
            self.calls[m].append((site, kind, cls, sub, base, ret))
        self.args = collections.defaultdict(dict)
        for site, i, a in load("Arg"):
            self.args[site][int(i)] = a
        self.formals = collections.defaultdict(dict)
        for m, i, v in load("FormalParam"):
            self.formals[m][int(i)] = v
        self.this = {m: v for m, v in load("ThisVar")}
        self.rets = collections.defaultdict(list)
        for m, v in load("RetVar"):
            self.rets[m].append(v)
        self.decl = {}
        for cls, sub, sig, st, conc in load("MethodDecl"):
            if conc == "concrete":
                self.decl[(cls, sub)] = sig
        self.supers = collections.defaultdict(list)
        for c, s in load("Super"):
            self.supers[c].append(s)
        self.classes = {c for c, _ in load("Class")}
        self.subtypes = collections.defaultdict(set)
        for c in self.classes:
            for s in self.ancestors(c):
                self.subtypes[s].add(c)

    def ancestors(self, c):
        out, stack = set(), [c]
        while stack:
            k = stack.pop()
            if k in out:
                continue
            out.add(k)
            stack.extend(self.supers.get(k, []))
        return out

    def dispatch(self, cls, sub):
        k = cls
        while k in self.classes:
            if (k, sub) in self.decl:
                return self.decl[(k, sub)]
            sup = [s for s in self.supers.get(k, []) if s in self.classes]
            k = sup[0] if sup else None
        return None

    def targets(self, kind, cls, sub):
        if kind in ("static", "special"):
            t = self.dispatch(cls, sub)
            return [t] if t else []
        return sorted({t for d in self.subtypes.get(cls, ()) for t in [self.dispatch(d, sub)] if t})


def pointsto(P, methods, lib_rets):
    pts = collections.defaultdict(set)
    hf = collections.defaultdict(set)
    moves = []  # (to, from) var copies incl. interprocedural
    loads, stores = [], []
    for m in methods:
        rels = P.by_m[m]
        for to, site, _ in rels["Alloc"]:
            pts[to].add(site)
        moves += [(to, fr) for to, fr in rels["Move"]]
        loads += [(to, b, f) for to, b, f in rels["Load"]] + [(to, "static", f) for to, f in rels["SLoad"]]
        stores += [(b, f, fr) for b, f, fr in rels["Store"]] + [("static", f, fr) for f, fr in rels["SStore"]]
    for site, ret in lib_rets:
        pts[ret].add("lib:" + site)
    pts["static"].add("static")
    for m in methods:
        for site, kind, cls, sub, base, ret in P.calls[m]:
            for t in P.targets(kind, cls, sub):
                if t not in methods:
                    continue
                for i, a in P.args[site].items():
                    if i in P.formals[t] and not a.startswith(("str:", "-")):
                        moves.append((P.formals[t][i], a))
                if base != "-" and t in P.this:
                    moves.append((P.this[t], base))
                if ret != "-":
                    moves += [(ret, r) for r in P.rets[t]]
    changed = True
    while changed:
        changed = False
        for to, fr in moves:
            if not pts[fr] <= pts[to]:
                pts[to] |= pts[fr]
                changed = True
        for b, f, fr in stores:
            for h in pts[b]:
                if not pts[fr] <= hf[(h, f)]:
                    hf[(h, f)] |= pts[fr]
                    changed = True
        for to, b, f in loads:
            for h in pts[b]:
                if not hf[(h, f)] <= pts[to]:
                    pts[to] |= hf[(h, f)]
                    changed = True
    return pts, moves, loads, stores


def analyze(P, test, cat, holes, prices):
    entry = ["<%s.testcode.%s: void %s(javax.servlet.http.HttpServletRequest,javax.servlet.http.HttpServletResponse)>"
             % (APP, test, n) for n in ("doPost", "doGet")]
    methods, stack = set(), [m for m in entry if m in P.calls or m in P.by_m]
    while stack:
        m = stack.pop()
        if m in methods:
            continue
        methods.add(m)
        for site, kind, cls, sub, base, ret in P.calls[m]:
            stack.extend(P.targets(kind, cls, sub))
    lib_rets = [(site, ret) for m in methods for site, kind, cls, sub, base, ret in P.calls[m]
                if ret != "-" and not P.targets(kind, cls, sub)]
    pts, moves, loads, stores = pointsto(P, methods, lib_rets)

    G = nx.DiGraph()
    INF = float("inf")

    def code(a, b):
        if a != b:
            G.add_edge(a, b, capacity=INF)

    def objs(v):
        return [("h", h) for h in pts.get(v, ())]

    for to, fr in moves:
        code(("v", fr), ("v", to))
    for v, hs in list(pts.items()):
        for h in hs:
            code(("h", h), ("v", v))
    for to, b, f in loads:
        if b != "static":
            code(("v", b), ("v", to))  # tainted container/array variable taints what is read from it
        for h in pts[b]:
            code(("f", h, f), ("v", to))
            code(("h", h), ("v", to))
    for b, f, fr in stores:
        for h in pts[b]:
            code(("v", fr), ("f", h, f))
    cands = []
    nsinks = 0
    for m in methods:
        for site, kind, cls, sub, base, ret in P.calls[m]:
            if P.targets(kind, cls, sub):
                continue
            args = {i: a for i, a in P.args[site].items() if not a.startswith(("str:", "-"))}
            ends = dict(("arg%d" % i, a) for i, a in args.items())
            if base != "-":
                ends["this"] = base
            if ret != "-":
                ends["ret"] = ret
            if is_sink(cat, cls, sub):
                nsinks += 1
                for a in args.values():
                    code(("v", a), "SNK")
                    for h in pts[a]:
                        code(("f", h, "[]"), "SNK")
            if cls in SOURCE_CLASSES:
                rtype = sub[:sub.index(" ")]
                if ret != "-" and rtype in SOURCE_RET:
                    code("SRC", ("v", ret))
                    for o in objs(ret):
                        code("SRC", o)
                continue
            if cat == "xss" and cls.startswith(SANITIZERS):
                continue

            def tgt_nodes(t):
                return [("v", ends[t])] + ([] if t == "ret" else objs(ends[t]))

            key = (cls, sub)
            if cls.startswith("java."):
                h = holes.get(key)
                if not h:
                    continue
                for k, a in enumerate(h["atoms"]):
                    if a["src"] not in ends or a["tgt"] not in ends:
                        continue
                    mid = ("c", site, k)
                    p = prices[key][k]
                    G.add_edge(("v", ends[a["src"]]), mid, capacity=p)
                    for t in tgt_nodes(a["tgt"]):
                        code(mid, t)
                    cands.append({"site": site, "fact": "%s|%s|%s>%s" % (cls, sub, a["src"], a["tgt"]),
                                  "label": a["label"], "p": p, "mid": mid})
            else:
                srcs = [e for e in ends if e != "ret"]
                for s in srcs:
                    for t in ends:
                        if t != s and (t == "ret" or s != "this"):
                            for n in tgt_nodes(t):
                                code(("v", ends[s]), n)
    return G, cands, nsinks, len(methods)


def reach(G, allowed):
    """SRC reaches SNK using code edges and candidate edges whose mid node is in `allowed`."""
    if "SRC" not in G or "SNK" not in G:
        return False
    seen, stack = {"SRC"}, ["SRC"]
    while stack:
        n = stack.pop()
        for s in G.successors(n):
            if s in seen:
                continue
            if isinstance(s, tuple) and s[0] == "c" and s not in allowed:
                continue
            if s == "SNK":
                return True
            seen.add(s)
            stack.append(s)
    return False


def main():
    pricing = sys.argv[1] if len(sys.argv) > 1 else "choice"
    P = Program()
    holes = {(r["cls"], r["sig"]): r for r in map(json.loads, open(os.path.join(ROOT, "data/holes.jsonl")))}
    prices = collections.defaultdict(list)
    for rep in range(3):
        for d in map(json.loads, open(os.path.join(ROOT, "data/jev_holes_%s_r%d.jsonl" % (pricing, rep)))):
            prices[(d["cls"], d["sig"])].append(d["p"])
    prices = {k: [sum(x) / len(x) for x in zip(*v)] for k, v in prices.items()}
    rows = [r for r in csv.reader(open(os.path.join(ROOT, "bench/BenchmarkJava/expectedresults-1.2.csv")))
            if not r[0].startswith("#") and r[1] in TAINT_CATS]
    out = open(os.path.join(ROOT, "data/tests_%s.jsonl" % pricing), "w")
    for test, cat, real, cwe in rows:
        G, cands, nsinks, nm = analyze(P, test, cat, holes, prices)
        true_mids = {c["mid"] for c in cands if c["label"]}
        rec = {"test": test, "cat": cat, "owasp_real": real == "true", "sinks": nsinks, "methods": nm,
               "cands": len(cands), "truth": reach(G, true_mids), "unsound": reach(G, set()),
               "over": reach(G, {c["mid"] for c in cands})}
        if rec["unsound"]:
            rec["bound"] = None  # reported even without any hole fact
            rec["cut"] = []
        elif rec["over"]:
            val, (S, T) = nx.minimum_cut(G, "SRC", "SNK")
            rec["bound"] = val
            cut = [c for c in cands if c["mid"] in T and any(u in S for u in G.predecessors(c["mid"]))]
            rec["cut"] = [{"fact": c["fact"], "p": c["p"], "label": c["label"]} for c in cut]
        else:
            rec["bound"] = 0.0
            rec["cut"] = []
        rec["prices"] = {c["fact"] + "@" + c["site"]: [c["p"], c["label"]] for c in cands}
        out.write(json.dumps(rec) + "\n")
    out.close()


if __name__ == "__main__":
    main()
