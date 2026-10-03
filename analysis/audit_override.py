"""Write data/audit_override.json: the audit's final answers as labels for evaluate.py (pricing au-...).

Reads data/audit/audit_facts.csv (first pass), audit_recheck.csv (strict recheck of the yes rows) and audit_unsure.csv.
yes -> true, no -> false, unsure -> null (the flow is unknown, so verdicts that depend on it become undetermined).
Keys are "cls<TAB>sig<TAB>src<TAB>tgt" with src / tgt as this, ret, argN.
"""
import csv, json, os, re

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
    ENDP = {"the receiver object (this)": "this", "the return value": "ret"}
    ep = lambda e: ENDP.get(e) or "arg" + re.match(r"argument (\d+)", e).group(1)
    out = {}
    for i, r in A.items():
        out["\t".join((r["class"], r["method"], ep(r["secret_starts_in"]), ep(r["does_it_end_up_in"])))] = {"yes": True, "no": False}.get(final[i])
    json.dump(out, open(os.path.join(ROOT, "data/audit_override.json"), "w"))
    import collections
    print("audit override:", dict(collections.Counter(str(v) for v in out.values())))


if __name__ == "__main__":
    main()
