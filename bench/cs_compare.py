"""Library-model case study: TaintBench's documented leaks found by FlowDroid under each summary set.

Usage: cs_compare.py VARIANT [VARIANT ...]     (reads data/flowdroid_cs/<VARIANT>/{xml,logs,progress.log})
A documented (positive) leak counts as found when one FlowDroid result has a sink in the same class and method calling the
same API as the documented sink, and a source in the same class and method calling the same API as the documented source.
Apps where FlowDroid failed (no XML and no "Found 0 leaks" in the log) are reported separately. Also reports, per variant,
FlowDroid's results that match a documented negative (a flow TaintBench says is not a leak).
"""
import collections, glob, html, json, os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(ir):
    m = re.search(r"<([^>]+)>", ir or "")
    return m.group(1) if m else ""


def name_of(src_level):
    m = re.search(r"([\w$<>]+)\s*\(", src_level)
    return m.group(1) if m else src_level


def fd_results(path):
    out = []
    root = ET.parse(path).getroot()
    for r in root.iter("Result"):
        sk = r.find("Sink")
        sm = re.match(r"<([^:]+): \S+ ([^(]+)\(", html.unescape(sk.get("Method")))
        sinks = (sm.group(1), sm.group(2), html.unescape(sk.get("MethodSourceSinkDefinition", "")).strip("<>"))
        srcs = set()
        for s in r.iter("Source"):
            m = re.match(r"<([^:]+): \S+ ([^(]+)\(", html.unescape(s.get("Method")))
            if m:
                srcs.add((m.group(1), m.group(2), html.unescape(s.get("MethodSourceSinkDefinition", "")).strip("<>")))
        out.append((sinks, srcs))
    return out


def main():
    docs = {}
    for f in glob.glob(os.path.join(ROOT, "bench/taintbench/findings/findings/*_findings.json")):
        d = json.load(open(f))
        docs["tb_" + d["fileName"][:-4]] = d["findings"]
    print("| Variant | Apps answered | Documented leaks in answered apps | Found | Documented negatives reported |")
    print("| --- | --- | --- | --- | --- |")
    found_by = {}
    for v in sys.argv[1:]:
        base = os.path.join(ROOT, "data/flowdroid_cs", v)
        answered, found, total, neg = 0, set(), 0, 0
        for line in open(os.path.join(base, "progress.log")):
            app, rc, xmlok = line.split()[:3]
            xmlp = os.path.join(base, "xml", app + ".xml")
            if xmlok == "xml=yes":
                res = fd_results(xmlp)
            elif "Found 0 leaks" in open(os.path.join(base, "logs", app + ".log"), errors="replace").read():
                res = []
            else:
                continue
            answered += 1
            for fdg in docs.get(app, []):
                sk, so = fdg["sink"], fdg["source"]
                key_sink = (sk["className"], name_of(sk["methodName"]), api(" ".join(x["IRstatement"] for x in sk.get("IRs", []))))
                key_src = (so["className"], name_of(so["methodName"]), api(" ".join(x["IRstatement"] for x in so.get("IRs", []))))
                hit = any(s == key_sink and key_src in srcs for s, srcs in res)
                if fdg.get("isNegative"):
                    neg += hit
                else:
                    total += 1
                    if hit:
                        found.add((app, fdg["ID"]))
        found_by[v] = found
        print("| %s | %d | %d | %d | %d |" % (v, answered, total, len(found), neg))
    if "base" in found_by:
        for v, f in found_by.items():
            if v != "base":
                print("%s: new documented leaks over base %d, lost %d" % (v, len(f - found_by["base"]), len(found_by["base"] - f)))


if __name__ == "__main__":
    main()
