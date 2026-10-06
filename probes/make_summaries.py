"""Case study (which library models should FlowDroid's maintainers write next?): rank unmodeled framework methods and write
FlowDroid summaries for the top K of each ranking.

Usage: make_summaries.py K [RESULTS]     (RESULTS default data/android_choice-obj.jsonl, threshold 0.3)
Rankings of the methods FlowDroid does not model (hole source "none"):
  receipts   number of hole-dependent verdicts not cleared at the threshold whose receipt contains one of the method's facts
  frequency  number of apps that call the method (what a maintainer without receipts might use)
  random     a random order (seed 0)
For each ranking, the top K methods get a summary with the flows the answer key says are real: K2 (StubDroid on the Android
code, lenient) where it decides the fact, otherwise the main key. Output: data/summaries_<ranking>_<K>/ = FlowDroid's own
summaries (data/stubdroid) plus the new methods, merged into the class file when it exists; and data/summaries_<ranking>_<K>.json
listing the chosen methods and their flows.
"""
import collections, json, os, random, re, shutil, sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis"))
from evaluate import ROOT, key_holes, labelled_holes


def endpoint(e):
    if e == "this":
        return '<%s sourceSinkType="Field" />'
    if e == "ret":
        return '<%s sourceSinkType="Return" />'
    m = re.match(r"arg(\d+)$", e)
    return '<%%s sourceSinkType="Parameter" ParameterIndex="%s" />' % m.group(1)


def method_xml(sig, flows):
    out = ['\t\t<method id="%s">' % escape(sig, {'"': "&quot;"}), "\t\t\t<flows>"]
    for s, t in flows:
        out += ['\t\t\t\t<flow isAlias="%s" typeChecking="false">' % ("true" if (s, t) == ("this", "ret") else "false"),
                "\t\t\t\t\t" + endpoint(s) % "from", "\t\t\t\t\t" + endpoint(t) % "to", "\t\t\t\t</flow>"]
    out += ["\t\t\t</flows>", "\t\t</method>"]
    return "\n".join(out)


def write_dir(name, chosen):
    base = os.path.join(ROOT, "data/stubdroid")
    out = os.path.join(ROOT, "data", name)
    if os.path.exists(out):  # a directory this script wrote earlier
        shutil.rmtree(out)
    shutil.copytree(base, out)
    by_cls = collections.defaultdict(list)
    for cls, sig, flows in chosen:
        if flows:
            by_cls[cls].append(method_xml(sig, flows))
    for cls, methods in by_cls.items():
        path = os.path.join(out, cls.replace("$", "%24") + ".xml")
        if os.path.exists(path):
            s = open(path).read()
            if "<methods>" in s:
                s = s.replace("<methods>", "<methods>\n" + "\n".join(methods), 1)
            else:
                s = s.replace("</summary>", "\t<methods>\n%s\n\t</methods>\n</summary>" % "\n".join(methods), 1)
        else:
            s = '<?xml version="1.0" encoding="UTF-8"?>\n<summary fileFormatVersion="101">\n\t<methods>\n%s\n\t</methods>\n</summary>\n' % "\n".join(methods)
        open(path, "w").write(s)
    json.dump([{"cls": c, "sig": g, "flows": f} for c, g, f in chosen], open(out + ".json", "w"), indent=0)
    print(name, "methods", len(chosen), "with at least one real flow", sum(1 for _, _, f in chosen if f), "flows", sum(len(f) for _, _, f in chosen))


def main():
    k = int(sys.argv[1])
    res = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data/android_choice-obj.jsonl")
    main_key, k2 = labelled_holes(), key_holes("k2")
    unmodeled = {key for key, h in main_key.items() if h["source"] in ("none", "silver") and h["atoms"]}
    blocked = collections.Counter()
    for l in open(res):
        r = json.loads(l)
        if r["bound"] is None or r["bound"] <= 0.3:
            continue
        for m in {(c["cls"], c["sub"]) for c in r["cut"]}:
            if m in unmodeled:
                blocked[m] += 1
    hf = {(r["cls"], r["sig"]): r.get("apps", 0) for r in map(json.loads, open(os.path.join(ROOT, "data/holes_android_fw.jsonl")))}
    rankings = {"receipts": sorted(unmodeled, key=lambda m: (-blocked[m], m)),
                "frequency": sorted(unmodeled, key=lambda m: (-hf.get(m, 0), m))}
    rnd = sorted(unmodeled)
    random.Random(0).shuffle(rnd)
    rankings["random"] = rnd

    def flows(m):
        out = []
        for i, a in enumerate(main_key[m]["atoms"]):
            k2a = k2.get(m, {"atoms": []})["atoms"]
            lab = k2a[i]["label"] if i < len(k2a) and k2a[i]["label"] is not None else a["label"]
            if lab is True:
                out.append((a["src"], a["tgt"]))
        return out
    for name, order in rankings.items():
        write_dir("summaries_%s_%d" % (name, k), [(c, g, flows((c, g))) for c, g in order[:k]])
        print("  top 5:", [(c.split(".")[-1], g.split("(")[0].split(" ")[-1], blocked[(c, g)], hf.get((c, g))) for c, g in order[:5]])


if __name__ == "__main__":
    main()
