"""Compare two evaluation result files record by record (same sinks, bounds and receipts).

Usage: compare_results.py OLD.jsonl NEW.jsonl
A record is identical when truth, reports and bound match and the cut is the same set of facts.
Prints how many records differ and the first few differences.
"""
import json, sys


def load(path):
    out = {}
    for l in open(path):
        r = json.loads(l)
        out[(r["app"], r["site"])] = (r["truth_lo"], r["truth_hi"], json.dumps(r["rep"], sort_keys=True), r["bound"],
                                      frozenset((c["cls"], c["sub"], c["k"], c["src"], c["tgt"]) for c in r["cut"]))
    return out


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    only_a, only_b = set(a) - set(b), set(b) - set(a)
    diff = [k for k in set(a) & set(b) if a[k] != b[k]]
    print("records: old %d, new %d | only in old %d, only in new %d | differing %d" % (len(a), len(b), len(only_a), len(only_b), len(diff)))
    for k in diff[:5]:
        print("  DIFF", k[0], k[1][:70], "bound", a[k][3], "->", b[k][3], "cut sizes", len(a[k][4]), len(b[k][4]))
    print("IDENTICAL" if not (only_a or only_b or diff) else "NOT IDENTICAL")


if __name__ == "__main__":
    main()
