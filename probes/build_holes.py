"""Build the hole set for every JDK method called from the taint-category Benchmark tests.

Labels come from FlowDroid manual summaries resolved through the type hierarchy:
  summary       method found in the summary of the class or a supertype
  implicit-neg  a (super)type has a summary file but it omits this method -> no flows
  gap           summarized with callbacks/implicit flows (not in our atom language)
  none          no summary anywhere in the hierarchy -> label unknown
Output: data/holes.jsonl
"""
import collections, csv, glob, json, os, subprocess
import xml.etree.ElementTree as ET
from build_libflow import ROOT, base, close_flows, menu

TAINT_CATS = {"cmdi", "pathtraver", "sqli", "xss", "ldapi", "xpathi", "trustbound"}


def summaries(pattern="java.*.xml", subdir="stubdroid"):
    """class -> {subsig: flows or 'gap'}; subdir picks the summary set (FlowDroid manual or StubDroid generated)"""
    out = collections.defaultdict(dict)
    for f in glob.glob(os.path.join(ROOT, "data", subdir, pattern)):
        cls = os.path.basename(f)[:-4].replace("%24", "$")
        out[cls]  # a file exists even if it only declares hierarchy
        for m in ET.parse(f).getroot().iter("method"):
            if any(e.get("sourceSinkType") in ("GapBaseObject", "Implicit")
                   for fl in m.iter("flow") for e in fl):
                out[cls][m.get("id")] = "gap"
                continue
            flows = set()
            rt = m.get("id").split(" ")[0]
            for fl in m.iter("flow"):
                a, b = base(fl.find("from"), rt), base(fl.find("to"), rt)
                if a and b and a != b:
                    flows.add((a, b))
            out[cls][m.get("id")] = close_flows(m, flows)
    return out


def called_methods():
    cats = {r[0]: r[1] for r in csv.reader(open(os.path.join(ROOT, "bench/BenchmarkJava/expectedresults-1.2.csv")))
            if not r[0].startswith("#")}
    called = collections.Counter()
    for line in open(os.path.join(ROOT, "facts/Call.facts")):
        site, m, kind, cls, sub, b, ret = line.rstrip("\n").split("\t")
        test = m[1:m.index(":")].split("$")[0].split(".")[-1]
        if cats.get(test) in TAINT_CATS and cls.startswith("java."):
            called[(cls, sub)] += 1
    return called


def java(prog, lines):
    return subprocess.run(["java", os.path.join(ROOT, "probes", prog)], input="".join(lines),
                          capture_output=True, text=True, check=True).stdout.splitlines()


def main():
    summ = summaries()
    called = called_methods()
    keys = sorted(called)
    supers = dict(l.split("\t") for l in java("Supers.java", sorted({c + "\n" for c, _ in keys})))
    kinds = {}
    for line in java("Sigs.java", ["%s\t%s\n" % k for k in keys]):
        found, kind, cls, sig = line.split("\t")
        kinds[(cls, sig)] = kind if found == "found" else None
    stats = collections.Counter()
    with open(os.path.join(ROOT, "data/holes.jsonl"), "w") as f:
        for cls, sig in keys:
            chain = [c for c in supers.get(cls, "").split(",") if c] or [cls]
            source, flows = "none", None
            for c in chain:
                if c in summ and sig in summ[c]:
                    source, flows = ("gap", None) if summ[c][sig] == "gap" else ("summary:" + c, summ[c][sig])
                    break
            else:
                # a summary file on a real supertype means FlowDroid modeled the class and
                # omitted this method; java.lang.Object's file says nothing about subclasses
                if any(c in summ and c != "java.lang.Object" for c in chain):
                    source, flows = "implicit-neg", set()
            r = {"cls": cls, "sig": sig, "kind": kinds.get((cls, sig)), "source": source.split(":")[0],
                 "summary_cls": source.split(":")[1] if ":" in source else None, "calls": called[(cls, sig)]}
            if r["kind"] is None:
                stats["unresolved-kind"] += called[(cls, sig)]
                continue
            r["atoms"] = [{"src": s, "tgt": t, "label": None if flows is None else (s, t) in flows}
                          for s, t in menu(r)]
            stats[r["source"]] += called[(cls, sig)]
            stats[r["source"] + "-methods"] += 1
            f.write(json.dumps(r) + "\n")
    print(dict(stats))


if __name__ == "__main__":
    main()
