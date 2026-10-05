"""Budgeted verification: choose which receipt facts a checker should verify, without looking at any answer.

Usage: verify_select.py PRICING [--delta D] [--budgets 10,25,...] [--policy value|count|random] [--tag TAG]
Reads the receipts of data/android_<PRICING>.jsonl (all apps) and scores every fact (method, candidate index) that appears in
the receipt of a verdict not cleared at threshold D:
  unlock  (1 - price) times the number of those verdicts whose bound would drop to D or below if the fact alone were
          verified absent (the expected number of verdicts a "no" clears; default)
  value   sum over those verdicts of the fact's price (how much bound the answer can remove)
  count   number of those verdicts
  random  a random order of the same facts (seed 0)
The ranking uses prices and receipts only, never a label, and is a symmetric function of all apps, so it does not break the
exchangeability that the calibration needs. Writes data/verify/<TAG><POLICY>_<K>.json (lists of [cls, sub, k]) for each
budget K; evaluate.py reads one through VERIFY_FILE.
"""
import argparse, collections, json, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pricing")
    ap.add_argument("--delta", type=float, default=0.3)
    ap.add_argument("--budgets", default="10,25,50,100,200,400")
    ap.add_argument("--policy", default="unlock", choices=("unlock", "value", "count", "random"))
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    score = collections.Counter()
    for l in open(os.path.join(ROOT, "data/android_%s.jsonl" % a.pricing)):
        r = json.loads(l)
        if r["bound"] is None or r["bound"] <= a.delta:
            continue
        for c in r["cut"]:
            f = (c["cls"], c["sub"], c["k"])
            if a.policy == "unlock":
                if r["bound"] - c["p"] <= a.delta:
                    score[f] += 1 - c["p"]
                else:
                    score[f] += 0
            else:
                score[f] += c["p"] if a.policy == "value" else 1
    facts = sorted((f for f in score if score[f] > 0 or a.policy == "random"), key=lambda f: (-score[f], f))
    if a.policy == "random":
        random.Random(0).shuffle(facts)
    os.makedirs(os.path.join(ROOT, "data/verify"), exist_ok=True)
    print("facts in receipts of uncleared verdicts:", len(facts))
    for k in map(int, a.budgets.split(",")):
        out = os.path.join(ROOT, "data/verify/%s%s_%d.json" % (a.tag, a.policy, k))
        json.dump([list(f) for f in facts[:k]], open(out, "w"))
        print(out, "top score %.1f, k-th score %.2f" % (score[facts[0]], score[facts[min(k, len(facts)) - 1]]))
    for f in facts[:10]:
        print("  %.1f  %s  %s  #%d" % (score[f], f[0], f[1], f[2]))


if __name__ == "__main__":
    main()
