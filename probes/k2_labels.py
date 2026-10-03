"""K2 labels: StubDroid summaries generated from the real Android 13 implementation (android-all).

Usage: k2_labels.py [AUDIT_FACTS_CSV]
For every fact of the audit sheet (class, method, source, target) look the method up along the class's
superclass chain in data/stubdroid_gen/*.xml (written by tools/k2_one.sh) and answer
  yes     the generated summary has the flow (after the same closure of builder-style flows as the FlowDroid labels)
  no      the method's declaring class was summarized and the summary has no such flow
  gap     the summary contains a flow through a callee the generator could not resolve (unknown)
  unknown the declaring class has no generated summary (generation failed or was skipped)
Writes data/audit_private/k2_for_facts.csv with columns id, k2.
"""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_holes import summaries
from build_libflow import ROOT, menu

SKIP = {"java.lang.Object"}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/audit/audit_facts.csv")
    summ = summaries("*.xml", subdir="stubdroid_gen")
    sup = {c: s.split(",") for c, s in (l.split("\t") for l in open(os.path.join(ROOT, "data/android_supers.tsv")).read().splitlines())}
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    ENDP = {"the receiver object (this)": "this", "the return value": "ret"}
    out = []
    for r in rows:
        def ep(e):
            return ENDP.get(e) or "arg" + re.match(r"argument (\d+)", e).group(1)
        src, tgt = ep(r["secret_starts_in"]), ep(r["does_it_end_up_in"])
        chain = [c for c in sup.get(r["class"], []) if c] or [r["class"]]
        verdict = None
        for c in chain:
            if c in SKIP:
                continue
            if c in summ and r["method"] in summ[c]:
                f = summ[c][r["method"]]
                verdict = "gap" if f == "gap" else ("yes" if (src, tgt) in f else "no")
                break
        if verdict is None:
            have = [c for c in chain if c not in SKIP]
            verdict = "no" if have and all(c in summ for c in have) else "unknown"
        out.append((r["id"], verdict))
    os.makedirs(os.path.join(ROOT, "data/audit_private"), exist_ok=True)
    with open(os.path.join(ROOT, "data/audit_private/k2_for_facts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "k2"])
        w.writerows(out)
    import collections
    print("classes with a generated summary:", len(summ), "| K2 answers on %d facts:" % len(rows), dict(collections.Counter(v for _, v in out)))


if __name__ == "__main__":
    main()
