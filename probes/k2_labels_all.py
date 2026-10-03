"""K2 labels for every candidate flow of the framework hole file, as an answer key for evaluate.py (pricing k2-...).

Usage: k2_labels_all.py
Writes data/k2_labels.json: {"cls<TAB>sig": {"lenient": [true|false|null, ...], "strict": [...]}} with one entry per
atom in the order of data/holes_android_fw.jsonl. true = the generated summary has the flow; false = the method
was analyzed and has no such flow; null = unknown (not generated, not completed, or a flow through an unresolved
callee). "strict" also turns a "no" into null when the class log shows exceptions.
"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_libflow import ROOT
from k2_labels import load_context, verdicts

TO = {"yes": True, "no": False, "gap": None, "unknown": None}


def main():
    summ, sup, cache = load_context()
    out, cnt, strict_cnt = {}, collections.Counter(), collections.Counter()
    for l in open(os.path.join(ROOT, "data/holes_android_fw.jsonl")):
        h = json.loads(l)
        len_, st = [], []
        for a in h["atoms"]:
            v, s = verdicts(h["cls"], h["sig"], a["src"], a["tgt"], summ, sup, cache)
            len_.append(TO[v]); st.append(TO[s]); cnt[v] += 1; strict_cnt[s] += 1
        out[h["cls"] + "\t" + h["sig"]] = {"lenient": len_, "strict": st}
    json.dump(out, open(os.path.join(ROOT, "data/k2_labels.json"), "w"))
    print("classes with a summary:", len(summ), "| atoms: lenient", dict(cnt), "| strict", dict(strict_cnt))


if __name__ == "__main__":
    main()
