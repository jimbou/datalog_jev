"""Audit sheet: every library fact that an accepted receipt depends on, for an independent check.

Usage: audit_sheet.py [RESULTS_JSONL] [DELTA]   (default data/scale332/android_choice-obj.jsonl, 0.3)
A verdict is accepted when its bound is at most DELTA. Its receipt is the cut: the assumed-absent
library flows it depends on. A clearance is only as good as the answer key's claim that those flows
do not exist, so this lists each distinct fact once, with the question exactly as Jev was asked it.
Writes data/audit/audit_facts.csv (what the auditor sees: no key label, no price) and
data/audit_private/audit_key.csv (key label and source, Jev price, how many accepted sinks and apps
rely on the fact), kept apart so the auditor does not see it. Facts are ordered by the number of
accepted sinks that rely on them, so the first rows matter most.
"""
import collections, csv, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes"))
from run_jev import ROOT, WORDINGS, endpoint, state


def main():
    results = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/scale332/android_choice-obj.jsonl")
    delta = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
    kinds = {(r["cls"], r["sig"]): r["kind"] for r in map(json.loads, open(os.path.join(ROOT, "data/holes_android_fw.jsonl")))}
    facts = collections.OrderedDict()
    for l in open(results):
        r = json.loads(l)
        if r["bound"] is None or r["bound"] > delta or r["truth_lo"] != r["truth_hi"]:
            continue
        for c in r["cut"]:
            d = facts.setdefault((c["cls"], c["sub"], c["src"], c["tgt"]),
                                 {"label": c["label"], "source": c["source"], "p": c["p"],
                                  "clean": 0, "real": 0, "apps": set()})
            d["real" if r["truth_lo"] else "clean"] += 1
            d["apps"].add(r["app"])
    rows = sorted(facts.items(), key=lambda kv: -(kv[1]["clean"] + kv[1]["real"]))
    os.makedirs(os.path.join(ROOT, "data/audit"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "data/audit_private"), exist_ok=True)
    with open(os.path.join(ROOT, "data/audit/audit_facts.csv"), "w", newline="") as fa, \
            open(os.path.join(ROOT, "data/audit_private/audit_key.csv"), "w", newline="") as fk:
        wa, wk = csv.writer(fa), csv.writer(fk)
        wa.writerow(["id", "class", "method", "secret_starts_in", "does_it_end_up_in", "answer", "notes"])
        wk.writerow(["id", "key_label", "key_source", "jev_price", "accepted_clean_sinks", "accepted_real_sinks", "apps"])
        for i, ((cls, sub, src, tgt), d) in enumerate(rows, 1):
            r = {"cls": cls, "sig": sub, "kind": kinds.get((cls, sub), "instance")}
            _, params = state(r)
            q = WORDINGS["choice-obj"].format(src=endpoint(src, params), tgt=endpoint(tgt, params))
            wa.writerow([i, cls, sub, endpoint(src, params), endpoint(tgt, params), "", ""])
            wk.writerow([i, d["label"], d["source"], d["p"], d["clean"], d["real"], len(d["apps"])])
    n_wrong = sum(1 for _, d in rows if d["real"])
    print("accepted at delta <= %s: %d distinct facts; %d appear in a receipt of an accepted sink that the key calls real"
          % (delta, len(rows), n_wrong))
    print("by key source:", dict(collections.Counter(d["source"] for _, d in rows)))
    print("wrote data/audit/audit_facts.csv and data/audit_private/audit_key.csv")


if __name__ == "__main__":
    main()
