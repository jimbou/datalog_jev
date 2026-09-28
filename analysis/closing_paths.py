"""Closing loop, step 3: concrete source -> sink paths for witnessed flows FlowDroid misses.

For each atom that a witness test proved to be a flow (data/witness_results.jsonl) and that
FlowDroid's models leave out, find apps where that atom alone opens a sink in FlowDroid's world,
re-run Soufflé for those apps keeping node names, and print one shortest path per app:
source call -> methods passed through -> the hole -> sink call.
Usage: closing_paths.py [MAX_APPS_PER_ATOM]
Writes data/leak_paths.jsonl.
"""
import collections, glob, json, os, sys, tempfile
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from closing import app_candidates
from evaluate import MODELED, labelled_holes
from run_android import GRAPHS, ROOT, SCRATCH, framework_supers, prepare, rows, run_souffle, sources_sinks


def calls_by_ret_and_site(app_dir):
    """Call rows by site, and by result variable restricted to source calls (Soot reuses
    locals, so a variable can hold several call results; only the source call matters)."""
    sources = {tuple(l.rstrip("\n").split("\t")) for l in open(os.path.join(app_dir, "SourceMethod.facts"))}
    by_ret, by_site = {}, {}
    for l in open(os.path.join(app_dir, "Call.facts"), newline="\n"):
        p = l.rstrip("\n").split("\t")
        if len(p) == 7:
            by_site[p[0]] = p
            if p[6] != "-" and (p[3], p[4]) in sources:
                by_ret[p[6]] = p
    return by_ret, by_site


def method_of(node):
    """'v:<sig>/local' -> '<sig>' ; other node kinds -> None"""
    if node.startswith("v:") and ">/" in node:
        return node[2:node.rindex(">/") + 1]
    return None


def path_for(out, holes, atom, site):
    """Shortest SRC -> site path using code edges, FlowDroid-true candidates and `atom`."""
    succ = collections.defaultdict(list)
    for a, b in rows(out, "RelEdge"):
        succ[a].append(b)
    for mid, a, cls, sub, k in rows(out, "RelCand"):
        h = holes.get((cls, sub))
        k = int(k)
        ok = (cls, sub, k) == atom or (h and h["source"] in MODELED and h["atoms"][k]["label"] is True)
        if ok:
            succ[a].append(mid)
    starts = [n for n, in rows(out, "RelSrc")]
    goal = {n for s, n in rows(out, "RelSink") if s == site}
    prev = {s: None for s in starts}
    q = deque(starts)
    while q:
        u = q.popleft()
        if u in goal:
            p = []
            while u is not None:
                p.append(u)
                u = prev[u]
            return p[::-1]
        for v in succ[u]:
            if v not in prev:
                prev[v] = u
                q.append(v)
    return None


def main():
    per_atom = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    holes = labelled_holes()
    last = {}
    for d in map(json.loads, open(os.path.join(ROOT, "data/witness_results.jsonl"))):
        last[(d["cls"], d["sub"], d["k"])] = d
    targets = {a for a, d in last.items() if d["witness"] == "flow"}
    where = collections.defaultdict(list)  # atom -> [(app, sites)]
    for path in sorted(glob.glob(os.path.join(GRAPHS, "*.npz"))):
        app = os.path.basename(path)[:-4]
        for atom, sites in app_candidates(path, holes).items():
            if atom in targets:
                where[atom].append((app, sorted(sites)))
    supers, (src, snk) = framework_supers(), sources_sinks()
    out_f = open(os.path.join(ROOT, "data/leak_paths.jsonl"), "w")
    for atom in sorted(where, key=lambda a: -len(where[a])):
        for app, sites in where[atom][:per_atom]:
            app_dir = os.path.join(ROOT, "facts_apk_all", app)
            prepare(app_dir, holes, supers, src, snk)
            by_ret, by_site = calls_by_ret_and_site(app_dir)
            with tempfile.TemporaryDirectory(prefix="paths-", dir=SCRATCH) as out:
                if not run_souffle(app_dir, out):
                    continue
                p = path_for(out, holes, atom, sites[0])
            if not p:
                continue
            first = p[0]  # the search starts at the source nodes: a source call's result
            if first.startswith("h:lib:"):
                src_call = by_site.get(first[len("h:lib:"):])
            else:
                src_call = by_ret.get(first[2:])
            sink_call = by_site.get(sites[0])
            methods = []
            for n in p:
                m = method_of(n)
                if m and (not methods or methods[-1] != m):
                    methods.append(m)
            rec = {"atom": list(atom), "app": app, "sink_site": sites[0], "n_sites": len(sites),
                   "source": "%s.%s" % (src_call[3], src_call[4]) if src_call else first,
                   "sink": "%s.%s" % (sink_call[3], sink_call[4]) if sink_call else sites[0],
                   "methods": methods, "length": len(p)}
            out_f.write(json.dumps(rec) + "\n")
            out_f.flush()
            print("%s | %s.%s %s>%s\n  source: %s\n  sink:   %s\n  via:    %s" % (
                app, atom[0].split(".")[-1], atom[1].split("(")[0].split(" ")[-1], holes[atom[:2]]["atoms"][atom[2]]["src"],
                holes[atom[:2]]["atoms"][atom[2]]["tgt"], rec["source"], rec["sink"],
                "\n          ".join(m for m in methods[:8])), flush=True)
    out_f.close()


if __name__ == "__main__":
    main()
