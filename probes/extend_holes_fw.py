"""Add framework methods that appear in newly built graphs to data/holes_android_fw.jsonl.

Graphs built without keeping facts store the framework methods on their relevant paths
(hole_cls / hole_sub / hole_kind). Methods not yet in the framework hole file get a record with the
same labeling as build_holes_android.py; existing records are never changed, so prices and silver
labels already keyed by (class, signature) stay valid. Safe to re-run.
Usage: extend_holes_fw.py [--dry-run]   (env GRAPHS_DIRS: colon-separated graph directories, default data/graphs;
LIB_PREFIXES: a prefix file such as data/bundled_libs.txt, whose classes are holes in graphs built with it (F1 e))
"""
import collections, glob, json, os, shutil, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis"))
from build_holes import summaries
from build_holes_android import record
from run_android import ROOT, framework_supers

FW_FILE = os.path.join(ROOT, "data/holes_android_fw.jsonl")


def main():
    fw = {l.strip() for l in open(os.path.join(ROOT, "data/android_classes.txt"))}
    have = {(r["cls"], r["sig"]) for r in map(json.loads, open(FW_FILE))}
    lib = tuple(l.strip() for l in open(os.environ["LIB_PREFIXES"]) if l.strip() and not l.startswith("#")) \
        if os.environ.get("LIB_PREFIXES") else ()
    calls, apps, kinds = collections.Counter(), collections.defaultdict(set), {}
    dirs = os.environ.get("GRAPHS_DIRS", "data/graphs").split(":")
    for g in sorted(p for d in dirs for p in glob.glob(os.path.join(ROOT, d, "*.npz"))):
        z = np.load(g)
        if "hole_kind" not in z.files:
            continue
        app = os.path.basename(g)[:-4]
        for cls, sub, kind in zip(z["hole_cls"].tolist(), z["hole_sub"].tolist(), z["hole_kind"].tolist()):
            key = (cls, sub)
            if (cls in fw or (lib and cls.startswith(lib))) and key not in have:
                calls[key] += 1
                apps[key].add(app)
                kinds.setdefault(key, kind)
    summ = summaries("*.xml")
    supers = {c: ",".join(s) for c, s in framework_supers().items()}
    new = [record(c, s, kinds[(c, s)], calls[(c, s)], len(apps[(c, s)]), summ, supers) for c, s in sorted(calls)]
    new = [r for r in new if r["atoms"]]
    by_source = collections.Counter(r["source"] for r in new)
    print("new framework methods with atoms:", len(new), dict(by_source),
          "atoms:", sum(len(r["atoms"]) for r in new))
    if lib:
        print("of which bundled-library methods:", sum(not (r["cls"] in fw) for r in new))
    if "--dry-run" in sys.argv or not new:
        return
    shutil.copy(FW_FILE, FW_FILE + ".bak")
    with open(FW_FILE, "a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
