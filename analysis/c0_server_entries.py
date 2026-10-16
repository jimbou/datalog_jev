"""C0: share of hole-dependent verdicts whose sink is one of FlowDroid's non-Android source/sink entries (Java server
frameworks or generic Java, e.g. String.replace as a sink), on the apps whose facts are kept (facts_apk_all).

A verdict is a sink call site (data/android_fm-rk-choice-obj.jsonl, main setting); its sink API comes from Call.facts
(site -> called class and subsignature) restricted to the app's SinkMethod.facts. Groups by the called class:
Android (android., androidx., com.android., com.google.android., dalvik.), generic Java (java., javax. except servlet),
server frameworks (org.springframework., javax.servlet., org.owasp., org.hibernate., com.novell.), other libraries.
Source sites are counted the same way (app level; a verdict's sources are not stored).
Usage: python3 analysis/c0_server_entries.py RESULTS.jsonl
"""
import collections, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, "facts_apk_all")


def group(cls):
    if cls.startswith(("android.", "androidx.", "com.android.", "com.google.android.", "dalvik.")):
        return "Android"
    if cls.startswith(("org.springframework.", "javax.servlet.", "org.owasp.", "org.hibernate.", "com.novell.")):
        return "server framework"
    if cls.startswith(("java.", "javax.")):
        return "generic Java"
    return "other library"


rows = collections.defaultdict(list)
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r["bound"] is not None:
        rows[r["app"]].append(r)
apps = [a for a in sorted(rows) if os.path.isdir(os.path.join(F, a))]
cnt = collections.Counter(); hard = collections.Counter(); real = collections.Counter(); apis = collections.Counter()
srcs = collections.Counter()
for a in apps:
    sinkm = {tuple(l.rstrip("\n").split("\t")[:2]) for l in open(os.path.join(F, a, "SinkMethod.facts"))}
    srcm = {tuple(l.rstrip("\n").split("\t")[:2]) for l in open(os.path.join(F, a, "SourceMethod.facts"))}
    call = {}
    for l in open(os.path.join(F, a, "Call.facts"), newline="\n"):
        c = l.rstrip("\n").split("\t")
        call[c[0]] = (c[3], c[4])
        if (c[3], c[4]) in srcm:
            srcs[group(c[3])] += 1
    for r in rows[a]:
        k = call.get(r["site"])
        g = group(k[0]) if k and k in sinkm else "unmatched"
        cnt[g] += 1
        if r["truth_lo"] == r["truth_hi"]:
            (real if r["truth_lo"] else hard)[g] += 1
        if g != "Android" and k:
            apis[k] += 1
n = sum(cnt.values())
print("apps with kept facts and hole-dependent sinks: %d of %d; hole-dependent verdicts %d" % (len(apps), len(rows), n))
for g in ["Android", "generic Java", "server framework", "other library", "unmatched"]:
    print("  %-17s verdicts %6d (%5.1f%%)  hard slice %5d  real %5d" % (g, cnt[g], 100 * cnt[g] / n, hard[g], real[g]))
print("source call sites by group:", dict(srcs))
print("top non-Android sink APIs:", [("%s.%s" % k, v) for k, v in apis.most_common(8)])
