"""Hole set for every non-app method called from the sampled Android apps.

Methods come from stored facts (facts_apk_all/) and, for apps analysed without keeping facts, from
the hole lists stored in their graphs (data/graphs/). Only framework methods on some relevant
path are in a graph, which is all that later steps need.
Same labeling as build_holes.py (summary / implicit-neg / gap / none), over all 356
FlowDroid manual summaries; static-vs-instance comes from the call instruction.
Output: data/holes_android.jsonl
"""
import collections, glob, json, os, subprocess
from build_libflow import ROOT, menu
from build_holes import summaries


def main():
    summ = summaries("*.xml")
    called, kinds = collections.Counter(), {}
    apps = collections.defaultdict(set)
    for d in glob.glob(os.path.join(ROOT, "facts_apk_all/*")):
        app = os.path.basename(d)
        for line in open(os.path.join(d, "Call.facts"), newline="\n"):
            site, m, kind, cls, sub, b, ret = line.rstrip("\n").split("\t")
            if kind == "dynamic":
                continue
            key = (cls, sub)
            called[key] += 1
            apps[key].add(app)
            kinds[key] = "ctor" if " <init>(" in sub else ("static" if kind == "static" else "instance")
    # apps whose facts are not kept: their framework calls are recorded in the graphs
    import numpy as np
    for g in glob.glob(os.path.join(ROOT, "data/graphs/*.npz")):
        app = os.path.basename(g)[:-4]
        if os.path.isdir(os.path.join(ROOT, "facts_apk_all", app)):
            continue
        z = np.load(g)
        if "hole_kind" not in z:
            continue
        for cls, sub, kind in zip(z["hole_cls"].tolist(), z["hole_sub"].tolist(), z["hole_kind"].tolist()):
            called[(cls, sub)] += 1
            apps[(cls, sub)].add(app)
            kinds.setdefault((cls, sub), kind)
    classes = sorted({c for c, _ in called})
    out = subprocess.run(["java", "-cp", os.path.join(ROOT, "tools/android/android.jar"),
                          os.path.join(ROOT, "probes/Supers.java")], input="".join(c + "\n" for c in classes),
                         capture_output=True, text=True, check=True).stdout.splitlines()
    supers = dict(l.split("\t") for l in out)
    stats = collections.Counter()
    with open(os.path.join(ROOT, "data/holes_android.jsonl"), "w") as f:
        for (cls, sig), n in sorted(called.items()):
            chain = [c for c in supers.get(cls, "").split(",") if c] or [cls]
            source, flows = "none", None
            for c in chain:
                if c in summ and sig in summ[c]:
                    source, flows = ("gap", None) if summ[c][sig] == "gap" else ("summary", summ[c][sig])
                    break
            else:
                # a summary file on a real supertype means FlowDroid modeled the class and
                # omitted this method; java.lang.Object's file says nothing about subclasses
                if any(c in summ and c != "java.lang.Object" for c in chain):
                    source, flows = "implicit-neg", set()
            r = {"cls": cls, "sig": sig, "kind": kinds[(cls, sig)], "source": source, "calls": n,
                 "apps": len(apps[(cls, sig)])}
            r["atoms"] = [{"src": s, "tgt": t, "label": None if flows is None else (s, t) in flows}
                          for s, t in menu(r)]
            if r["atoms"]:
                stats[source] += n
                stats[source + "-methods"] += 1
                stats[source + "-atoms"] += len(r["atoms"])
            f.write(json.dumps(r) + "\n")
    print(dict(stats))


if __name__ == "__main__":
    main()
