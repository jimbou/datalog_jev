"""FlowDroid with its library summaries against FlowDroid with no library model, on the same apps.

Usage: flowdroid_none_compare.py
Reads data/flowdroid (summaries: -tw STUBDROID) and data/flowdroid_none (no library model: -tw NONE). A leak is identified by the
method that contains the sink call. A leak found with the summaries and not without them is a leak that the tool misses when library
behavior is unmodeled: the unsoundness this project bounds. Apps where either run failed (timeout, error) are excluded; apps where a
run stopped at FlowDroid's own memory limit are shown separately because their result is partial.
"""
import collections, glob, os, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(sub):
    fd, state = {}, {}
    prog = os.path.join(ROOT, "data", sub, "progress.log")
    for line in open(prog).read().splitlines():
        w = line.split()
        if len(w) >= 3 and w[2] == "xml=no":
            log = os.path.join(ROOT, "data", sub, "logs", w[0] + ".log")
            if os.path.exists(log) and "Found 0 leaks" in open(log, errors="replace").read():
                fd[w[0]], state[w[0]] = set(), "NoLeaks"
    for p in glob.glob(os.path.join(ROOT, "data", sub, "xml", "*.xml")):
        app = os.path.basename(p)[:-4]
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            continue
        state[app] = root.get("TerminationState", "?")
        fd[app] = {r.find("Sink").get("Method") for r in root.iter("Result") if r.find("Sink") is not None}
    return fd, state


def main():
    a, sa = load("flowdroid")
    b, sb = load("flowdroid_none")
    both = sorted(set(a) & set(b))
    print("apps with an answer in both modes: %d (summaries only: %d, none only: %d)" % (len(both), len(set(a) - set(b)), len(set(b) - set(a))))
    print("%-44s %-10s %-10s %5s %5s %9s %9s" % ("app", "with", "without", "F_sum", "F_non", "only-sum", "only-non"))
    tot = collections.Counter()
    for app in both:
        s, n = a[app], b[app]
        partial = "DataFlowOutOfMemory" in (sa[app], sb[app])
        key = "partial" if partial else "complete"
        tot[key + "_apps"] += 1
        tot[key + "_F_sum"] += len(s)
        tot[key + "_F_non"] += len(n)
        tot[key + "_only_sum"] += len(s - n)
        tot[key + "_only_non"] += len(n - s)
        tot[key + "_apps_with_loss"] += 1 if (s - n) else 0
        if s or n:
            print("%-44s %-10s %-10s %5d %5d %9d %9d%s" % (app[:44], sa[app][:10], sb[app][:10], len(s), len(n), len(s - n), len(n - s), "  (partial)" if partial else ""))
    for key in ("complete", "partial"):
        print("\n%s runs: %d apps | leaking sink methods with summaries %d, without %d | found only with summaries %d (%.0f%% of those with summaries), only without %d | apps with at least one leak missed without summaries: %d" % (
            key, tot[key + "_apps"], tot[key + "_F_sum"], tot[key + "_F_non"], tot[key + "_only_sum"],
            100 * tot[key + "_only_sum"] / max(1, tot[key + "_F_sum"]), tot[key + "_only_non"], tot[key + "_apps_with_loss"]))
    allF = sum(len(a[x]) for x in both)
    allOnly = sum(len(a[x] - b[x]) for x in both)
    print("\nall apps with both answers: with summaries %d leaking sink methods; %d (%.0f%%) of them disappear without the library model" % (allF, allOnly, 100 * allOnly / max(1, allF)))


if __name__ == "__main__":
    main()
