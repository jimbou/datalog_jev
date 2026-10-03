"""K2 labels: StubDroid summaries generated from the real Android 13 implementation (android-all).

Usage: k2_labels.py [AUDIT_FACTS_CSV]
For every fact of the audit sheet (class, method, source, target) look the method up along the class's
superclass chain in data/stubdroid_gen/*.xml (written by tools/k2_one.sh) and answer
  yes      the generated summary has the flow (after the same closure of builder-style flows as the FlowDroid labels)
  no       the method was analyzed ("Method <...> done." in the generator log of a chain class) and the summary
           has no such flow
  gap      the summary has a flow through a callee the generator could not resolve (unknown)
  unknown  the method was never completed (class timeout, failure, or no log)
Two readings are written: k2 (lenient: a completed method is trusted) and k2_strict (a "no" additionally needs a
class log without any exception, because exceptions in the generator's path-reconstruction thread cannot be
attributed to one method and may have dropped flows). A found flow stays valid in both.
Writes data/audit_private/k2_for_facts.csv with columns id, k2, k2_strict.
"""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_holes import summaries
from build_libflow import ROOT, menu

SKIP = {"java.lang.Object"}
LOGS = os.path.join(ROOT, "data/stubdroid_gen_logs")
DONE = re.compile(r"Method <([^:>]+): (.+)> done\.")


def log_info(cls):
    """(set of (declaring class, signature) completed, True if the log has an exception) for one class."""
    p = os.path.join(LOGS, cls + ".log")
    if not os.path.exists(p):
        return set(), True
    t = open(p, errors="replace").read()
    done = {(m.group(1), m.group(2)) for m in DONE.finditer(t)}
    return done, bool(re.search(r"Exception|OutOfMemory|timed out", t))


def verdicts(cls, method, src, tgt, summ, sup, cache):
    """(lenient, strict) K2 answer for one candidate flow: yes / no / gap / unknown (see the module docstring)."""
    chain = [c for c in sup.get(cls, []) if c] or [cls]
    verdict, strict, found = None, None, None
    for c in chain:
        if c in SKIP:
            continue
        if c in summ and method in summ[c]:
            f = summ[c][method]
            found = "gap" if f == "gap" else ("yes" if (src, tgt) in f else "no")
            if found != "no":
                return found, found
            break
    # a method with no flow is only "no" if the generator finished it (in this class's or a subclass's log)
    ok = bad = False
    for lc in [cls] + [c for c in chain if c not in SKIP]:
        if lc not in cache:
            cache[lc] = log_info(lc)
        done, exc = cache[lc]
        if any(sig == method for _, sig in done):
            ok, bad = True, bad or exc
    if found == "no" or ok:
        return "no", ("unknown" if bad else "no")
    return "unknown", "unknown"


def load_context():
    summ = summaries("*.xml", subdir="stubdroid_gen")
    sup = {c: s.split(",") for c, s in (l.split("\t") for l in open(os.path.join(ROOT, "data/android_supers.tsv")).read().splitlines())}
    return summ, sup, {}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/audit/audit_facts.csv")
    summ, sup, cache = load_context()
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    ENDP = {"the receiver object (this)": "this", "the return value": "ret"}
    out = []
    for r in rows:
        def ep(e):
            return ENDP.get(e) or "arg" + re.match(r"argument (\d+)", e).group(1)
        v, st = verdicts(r["class"], r["method"], ep(r["secret_starts_in"]), ep(r["does_it_end_up_in"]), summ, sup, cache)
        out.append((r["id"], v, st))
    os.makedirs(os.path.join(ROOT, "data/audit_private"), exist_ok=True)
    with open(os.path.join(ROOT, "data/audit_private/k2_for_facts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "k2", "k2_strict"])
        w.writerows(out)
    import collections
    print("classes with a generated summary:", len(summ), "| K2 on %d facts: lenient" % len(rows), dict(collections.Counter(v for _, v, _ in out)),
          "| strict", dict(collections.Counter(v for _, _, v in out)))


if __name__ == "__main__":
    main()
