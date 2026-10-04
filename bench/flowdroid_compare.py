"""Compare FlowDroid's reported leaks with our analysis, per app and overall, at the level of sink-containing methods.

Usage: flowdroid_compare.py [RESULTS_JSONL]        (default data/android_choice-obj.jsonl)
Reads data/flowdroid/xml/*.xml (FlowDroid, same sources and sinks, default library summaries) and the per-sink records of our
evaluation. A FlowDroid leak is identified by the method that contains the sink call; one of our sink sites by the method in its id
("<class: signature>/index"). Three sets per app:
  F    methods with a sink that FlowDroid reports as reached by a source
  ALL  methods with a sink that our analysis reaches when every library hole is a flow (the sound over-approximation)
  REAL methods with a sink that our analysis reaches under the answer key (key-true flows only, or through code alone)
Reported: share of F contained in ALL (does our over-approximation cover FlowDroid?), in REAL, and share of REAL that FlowDroid
also reports. They differ in precision (FlowDroid is flow- and context-sensitive and models the lifecycle; our analysis is
context-insensitive), so the numbers describe agreement, not correctness.
"""
import collections, glob, json, os, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    results = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/android_choice-obj.jsonl")
    fd, state = {}, {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data/flowdroid/xml/*.xml"))):
        app = os.path.basename(p)[:-4]
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            continue
        state[app] = root.get("TerminationState", "?")
        fd[app] = {r.find("Sink").get("Method") for r in root.iter("Result") if r.find("Sink") is not None}
    ours_all, ours_real = collections.defaultdict(set), collections.defaultdict(set)
    for l in open(results):
        r = json.loads(l)
        if r["app"] not in fd:
            continue
        m = r["site"].rsplit("/", 1)[0]
        ours_all[r["app"]].add(m)
        if r["bound"] is None or r["truth_lo"]:
            ours_real[r["app"]].add(m)
    print("%-44s %-12s %4s %4s %5s | F in ALL  F in REAL  REAL in F" % ("app", "FlowDroid", "F", "ALL", "REAL"))
    tF = tA = tR = tFR = tRF = tREAL = 0
    for app in sorted(fd):
        F, A, R = fd[app], ours_all[app], ours_real[app]
        tF += len(F); tA += len(F & A); tR += len(F & R); tREAL += len(R); tRF += len(R & F)
        print("%-44s %-12s %4d %4d %5d | %5s    %5s      %5s" % (app[:44], state[app][:12], len(F), len(A), len(R),
              "%d/%d" % (len(F & A), len(F)), "%d/%d" % (len(F & R), len(F)), "%d/%d" % (len(R & F), len(R))))
    print("\napps with a FlowDroid result: %d | FlowDroid termination states: %s" % (len(fd), dict(collections.Counter(state.values()))))
    print("overall: FlowDroid's leaking sink methods %d; contained in our all-holes-on set %d (%.0f%%), in our key-true set %d (%.0f%%); "
          "our key-true sink methods %d, of which FlowDroid also reports %d (%.0f%%)" % (
              tF, tA, 100 * tA / max(1, tF), tR, 100 * tR / max(1, tF), tREAL, tRF, 100 * tRF / max(1, tREAL)))


if __name__ == "__main__":
    main()
