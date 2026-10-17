"""Key quality: a third labeler (Sonnet 5.5, rubric prompt with the written definition, cloud run 2026-10-17) on the 446
audited facts. Agreement with the audit's final answers, with each of the two key labelers (Sonnet 5, GPT-6.1 rubric
labels), with the main key where the two agree, and with the person's source checks (27 facts in human_source_check.csv,
40 in human_sample2.csv; row -> fact id from data/audit_private/human_sample2_meta.csv).

Usage: python3 analysis/third_labeler.py ORACLE_SONNET55.jsonl
Undecidable (null) labels and "unsure" answers are reported separately and left out of the agreement shares.
"""
import collections, csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDP = {"the receiver object (this)": "this", "the return value": "ret"}


def ep(e):
    return ENDP.get(e) or "arg" + re.match(r"argument (\d+)", e).group(1)


def rd(path):
    return list(csv.DictReader(open(os.path.join(ROOT, path), newline="", encoding="utf-8-sig")))


def labels(path):
    """(cls, sig, src, tgt) -> True / False / None, aligned with the atoms of data/audit_methods.jsonl."""
    atoms = {(r["cls"], r["sig"]): r["atoms"] for r in map(json.loads, open(os.path.join(ROOT, "data/audit_methods.jsonl")))}
    out = {}
    for d in map(json.loads, open(path if os.path.isabs(path) else os.path.join(ROOT, path))):
        a = atoms.get((d["cls"], d["sig"]))
        if a is None or "labels" not in d or len(d["labels"]) != len(a):
            continue
        for x, l in zip(a, d["labels"]):
            out[(d["cls"], d["sig"], x["src"], x["tgt"])] = l
    return out


def main():
    s55 = labels(sys.argv[1])
    s5 = labels("data/oracle-rubric-sonnet5.jsonl")
    gpt = labels("data/oracle-rubric-gpt61.jsonl")
    facts = {r["id"]: (r["class"], r["method"], ep(r["secret_starts_in"]), ep(r["does_it_end_up_in"])) for r in rd("data/audit/audit_facts.csv")}
    final = {i: r["answer"] for i, r in ((r["id"], r) for r in rd("data/audit/audit_facts.csv"))}
    for r in rd("data/audit/audit_recheck.csv"):
        final[r["id"]] = r["new_answer"]
    for r in rd("data/audit/audit_unsure.csv"):
        final[r["id"]] = r["answer"]
    human = {r["id"]: r["answer"].strip() for r in rd("data/audit/human_source_check.csv") if r["answer"].strip()}
    meta = {r["row"]: r["fact_id"] for r in rd("data/audit_private/human_sample2_meta.csv")}
    for r in rd("data/audit/human_sample2.csv"):
        if r["answer"].strip():
            human[meta[r["row"]]] = r["answer"].strip()
    yn = {"yes": True, "no": False}

    def agree(name, ref, lab=s55, who="sonnet55"):
        c = collections.Counter()
        for i, k in facts.items():
            a, b = lab.get(k, "missing"), ref(i, k)
            if a == "missing":
                c[who + " missing"] += 1
            elif b is None:
                c["reference undecided"] += 1
            elif a is None:
                c[who + " undecidable"] += 1
            else:
                c["agree" if a == b else "disagree"] += 1
                if a != b:
                    c[who + (" yes, reference no" if a else " no, reference yes")] += 1
        n = c["agree"] + c["disagree"]
        print("%-36s agree %d of %d (%.1f%%) | %s" % (name, c["agree"], n, 100 * c["agree"] / max(1, n),
              ", ".join("%s %d" % kv for kv in sorted(c.items()) if kv[0] not in ("agree", "disagree"))))

    print("audited facts", len(facts), "| Sonnet 5.5 labels for", sum(k in s55 for k in facts.values()))
    agree("audit final answers", lambda i, k: yn.get(final[i]))
    agree("Sonnet 5 (key labeler)", lambda i, k: s5.get(k))
    agree("GPT-6.1 (key labeler)", lambda i, k: gpt.get(k))
    agree("main key, both labelers agree", lambda i, k: s5.get(k) if s5.get(k) is not None and s5.get(k) == gpt.get(k) else None)
    agree("person's source checks (%d)" % len(human), lambda i, k: yn.get(human.get(i)))
    agree("  for comparison: Sonnet 5", lambda i, k: yn.get(human.get(i)), s5, "sonnet5")
    agree("  for comparison: GPT-6.1", lambda i, k: yn.get(human.get(i)), gpt, "gpt61")
    agree("  for comparison: audit answers", lambda i, k: yn.get(human.get(i)),
          {k: yn.get(final[i]) for i, k in facts.items()}, "audit")


if __name__ == "__main__":
    main()
