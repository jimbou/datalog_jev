"""Turn the FlowDroid receipts (bench/fd_receipts.py) into per-sink records that app_ltt.py calibrates.

Usage: fd_receipts_eval.py RECEIPTS_DIR PRICING OUT_TAG      e.g. data/fd_receipts_fdroid choice-obj fdr
Writes data/android_<OUT_TAG>-<PRICING>.jsonl. Per app with all three FlowDroid runs:
  - a sink FlowDroid reports with its own summaries is reported (bound None);
  - a sink reported only with the holes on is hole-dependent: if its receipt was confirmed by FlowDroid, its bound is the sum
    of the prices of every candidate flow of the switched-off methods (the whole methods were switched off, so the union
    bound runs over all their flows); otherwise its bound is infinite (never cleared);
  - its truth is whether FlowDroid with the key's real flows (and its own summaries) reports it.
Prices come from data/jev_holes_android_fw_<PRICING>_r0.jsonl (rows {cls, sig, p: [...]}); a method without a price counts 0.5
per candidate flow.
"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    rdir, pricing, tag = sys.argv[1:4]
    prices = {}
    for l in open(os.path.join(ROOT, "data/jev_holes_android_fw_%s_r0.jsonl" % pricing)):
        d = json.loads(l)
        if "p" in d:
            prices[(d["cls"], d["sig"])] = d["p"]
    holes = {(r["cls"], r["sig"]): r for r in map(json.loads, open(os.path.join(ROOT, "data/holes_android_fw.jsonl")))}
    out = os.path.join(ROOT, "data/android_%s-%s.jsonl" % (tag, pricing))
    n_app = n_hd = n_conf = 0
    with open(out, "w") as f:
        for p in sorted(glob.glob(os.path.join(ROOT, rdir, "*.json"))):
            d = json.load(open(p))
            if d.get("status") != "ok":
                continue
            n_app += 1
            truth = set(d["truth"])
            for s in d["base"]:
                f.write(json.dumps({"app": d["app"], "site": s, "truth_lo": True, "truth_hi": True, "bound": None, "cut": []}) + "\n")
            for s in d["on_only"]:
                n_hd += 1
                info = d["sinks"].get(s)
                if info and info["confirmed"]:
                    n_conf += 1
                    b = 0.0
                    for c, g in map(tuple, info["receipt"]):
                        n = len(holes.get((c, g), {"atoms": [0]})["atoms"])
                        b += sum(prices.get((c, g), [0.5] * n))
                    cut = [{"cls": c, "sub": g} for c, g in info["receipt"]]
                else:
                    b, cut = 1e9, []
                t = s in truth
                f.write(json.dumps({"app": d["app"], "site": s, "truth_lo": t, "truth_hi": t, "bound": b, "cut": cut}) + "\n")
    print("apps", n_app, "hole-dependent sinks", n_hd, "confirmed receipts", n_conf, "->", out)


if __name__ == "__main__":
    main()
