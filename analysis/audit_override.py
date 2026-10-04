"""Write data/audit_override.json (pricing au-...) or, with --human, data/audit_override_human.json (pricing ah-...):
the audit's final answers as labels for evaluate.py. --human lets the person's answers in
data/audit/human_source_check.csv replace the AI answers on those facts.

Reads data/audit/audit_facts.csv (first pass), audit_recheck.csv (strict recheck of the yes rows) and audit_unsure.csv.
yes -> true, no -> false, unsure -> null (the flow is unknown, so verdicts that depend on it become undetermined).
Keys are "cls<TAB>sig<TAB>src<TAB>tgt" with src / tgt as this, ret, argN.
"""
import csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(name):
    return list(csv.DictReader(open(os.path.join(ROOT, "data/audit", name), newline="", encoding="utf-8-sig")))


def main():
    A = {r["id"]: r for r in rd("audit_facts.csv")}
    final = {i: r["answer"] for i, r in A.items()}
    for r in rd("audit_recheck.csv"):
        final[r["id"]] = r["new_answer"]
    for r in rd("audit_unsure.csv"):
        final[r["id"]] = r["answer"]
    human = "--human" in sys.argv or "--sample2" in sys.argv
    if human:
        for r in rd("human_source_check.csv"):
            if r["answer"].strip():
                final[r["id"]] = r["answer"].strip()
    sample2 = "--sample2" in sys.argv
    if sample2:  # the second human check (40 facts the AI called no); row -> fact id comes from the private metadata
        meta = {r["row"]: r["fact_id"] for r in csv.DictReader(open(os.path.join(ROOT, "data/audit_private/human_sample2_meta.csv"), newline=""))}
        for r in rd("human_sample2.csv"):
            if r["answer"].strip():
                final[meta[r["row"]]] = r["answer"].strip()
    ENDP = {"the receiver object (this)": "this", "the return value": "ret"}
    ep = lambda e: ENDP.get(e) or "arg" + re.match(r"argument (\d+)", e).group(1)
    out = {}
    for i, r in A.items():
        out["\t".join((r["class"], r["method"], ep(r["secret_starts_in"]), ep(r["does_it_end_up_in"])))] = {"yes": True, "no": False}.get(final[i])
    name = "data/audit_override_human2.json" if sample2 else "data/audit_override_human.json" if human else "data/audit_override.json"
    json.dump(out, open(os.path.join(ROOT, name), "w"))
    import collections
    print("audit override:", dict(collections.Counter(str(v) for v in out.values())))


if __name__ == "__main__":
    main()
