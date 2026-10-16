"""F2: combine two existing pricers into a new price file (no new model calls).

Usage: python3 analysis/f2_combine.py MODE A B OUT
  MODE tie   A's price, ties broken by B (p = A + 1e-4 * B; only the order matters, Proposition 3)
       max   the higher of the two prices
       mean  the mean of the two prices
Reads data/jev_holes_android_fw_<A>_r0.jsonl and <B> (B may also be a path), writes
data/jev_holes_android_fw_<OUT>_r0.jsonl with A's methods. Where B has no price for a method (or a different number of
candidate flows), A's price is kept; the count is printed.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(tag):
    return tag if os.path.exists(tag) else os.path.join(ROOT, "data/jev_holes_android_fw_%s_r0.jsonl" % tag)


def main():
    mode, a, b, out = sys.argv[1:5]
    comb = {"tie": lambda x, y: x + 1e-4 * y, "max": max, "mean": lambda x, y: (x + y) / 2}[mode]
    pb = {}
    for l in open(path(b)):
        r = json.loads(l)
        if r.get("p"):
            pb[(r["cls"], r["sig"])] = r["p"]
    n = kept = 0
    with open(path(out), "w") as f:
        for l in open(path(a)):
            r = json.loads(l)
            if not r.get("p"):
                continue
            q = pb.get((r["cls"], r["sig"]))
            n += 1
            if q is None or len(q) != len(r["p"]):
                kept += 1
                p = r["p"]
            else:
                p = [comb(x, y) for x, y in zip(r["p"], q)]
            f.write(json.dumps({"cls": r["cls"], "sig": r["sig"], "p": p}) + "\n")
    print("%s %s(%s, %s): %d methods, %d without a price from %s (kept %s's)" % (out, mode, a, b, n, kept, b, a))


if __name__ == "__main__":
    main()
