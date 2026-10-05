"""TaintBench (experiment 3): documented malware leaks against our verdicts, and the F-Droid threshold on malware.

Usage: taintbench_compare.py RESULTS SOURCES_SINKS DELTA [DELTA ...]
  RESULTS        data/android_<pricing>_<tb|tbl>.jsonl (TaintBench graphs evaluated by evaluate.py)
  SOURCES_SINKS  the list the graphs were built with (data/SourcesAndSinks.txt or bench/taintbench/TB_SourcesAndSinks.txt)
  DELTA          thresholds certified on the 324 F-Droid apps (e.g. 0.03 for Sonnet at alpha 0.05)
Documented flows come from bench/taintbench/findings/findings/*.json (positive findings only). A flow is matched at the
level of the method that contains its sink (class and method name), as in the FlowDroid comparison; the source is not
matched, so "found" means our analysis reports a flow into a sink of that method. Each documented flow is one of:
  out of scope   its sink API is not in the sink list, or the app has no graph
  reported       a sink of that method is reachable without any hole (the unsound analysis reports it)
  needs holes    reachable only through holes: we give its smallest bound, and whether it is cleared at each DELTA
                 (a cleared documented leak is a wrong clearance by the benchmark's own truth)
  not reached    in scope, but no source reaches a sink of that method even with every hole open
Transfer: share of TaintBench apps with at least one wrong clearance (by our answer key) at each DELTA, next to the
F-Droid held-out rate.
"""
import collections, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sink_apis(path):
    out = set()
    for line in open(os.path.join(ROOT, path)):
        m = re.match(r"(?:\S+\s+)?<([^:>]+): ([^>]+)>.*?->\s*(_[A-Z]+_)", line.strip())
        if m and not line.startswith("%") and m.group(3) in ("_SINK_", "_BOTH_"):
            out.add("<%s: %s>" % (m.group(1), m.group(2)))
    return out


def method_name(src_level):
    m = re.search(r"([\w$<>]+)\s*\(", src_level)
    return m.group(1) if m else src_level


def main():
    res, ss, deltas = sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3:]]
    sinks = sink_apis(ss)
    by_method = collections.defaultdict(list)
    by_app = collections.defaultdict(list)
    for r in map(json.loads, open(os.path.join(ROOT, res))):
        m = re.match(r"<([^:]+): \S+ ([^(]+)\(", r["site"])
        by_method[(r["app"], m.group(1), m.group(2))].append(r)
        if r["bound"] is not None and r["truth_lo"] == r["truth_hi"]:
            by_app[r["app"]].append((r["bound"], r["truth_lo"]))
    apps = {r for r, _, _ in by_method}
    cats = collections.Counter()
    cleared = collections.Counter()
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "bench/taintbench/findings/findings/*_findings.json"))):
        d = json.load(open(f))
        app = "tb_" + d["fileName"][:-4]
        for fd in d["findings"]:
            if fd.get("isNegative"):
                continue
            sk = fd["sink"]
            ir = " ".join(x["IRstatement"] for x in sk.get("IRs", []))
            api = re.search(r"<[^>]+>", ir)
            api = api.group(0) if api else ""
            if app not in apps:
                cat = "out of scope (no graph)"
            elif api not in sinks:
                cat = "out of scope (sink API not in list)"
            else:
                recs = by_method.get((app, sk["className"], method_name(sk["methodName"])), [])
                if any(r["bound"] is None for r in recs):
                    cat = "reported without holes"
                elif recs:
                    cat = "needs holes"
                    b = min(r["bound"] for r in recs)
                    for dl in deltas:
                        if b <= dl:
                            cleared[dl] += 1
                    rows.append((app, fd["ID"], api, b, [r["truth_lo"] for r in recs if r["bound"] == b][0]))
                else:
                    cat = "not reached"
            cats[cat] += 1
    print("documented positive flows:", sum(cats.values()))
    for c, n in sorted(cats.items()):
        print("  %-38s %d" % (c, n))
    for dl in deltas:
        print("  needs holes and cleared at delta=%g (a documented leak wrongly cleared): %d" % (dl, cleared[dl]))
    for app, i, api, b, truth in sorted(rows, key=lambda x: x[3]):
        print("    %-34s #%-3s bound %.3f key-real %-5s %s" % (app, i, b, truth, api[:70]))
    print("transfer (apps of this benchmark with a hole-dependent verdict: %d)" % len(by_app))
    for dl in deltas:
        wrong = sum(any(real for b, real in v if b <= dl) for v in by_app.values())
        clean = sum(1 for v in by_app.values() for b, real in v if not real)
        acc = sum(1 for v in by_app.values() for b, real in v if b <= dl and not real)
        print("  delta=%g: apps with a wrong clearance %d/%d (%.1f%%), leak-free hole-dependent verdicts cleared %d/%d (%.1f%%)"
              % (dl, wrong, len(by_app), 100 * wrong / max(1, len(by_app)), acc, clean, 100 * acc / max(1, clean)))


if __name__ == "__main__":
    main()
