# F2 development subset, fixed 2026-10-16 before any F2 pricing: 30% of the 307 main apps (decided hole-dependent sinks
# under fm-rk-choice-obj), seed 20261016; the unmodeled hole methods (FlowDroid source none or gap) in their graphs;
# and a 30-method test set (seed 20261016) for the cloud-credit trial (paper/CLOUD_CREDITS_PLAN.md).
import json, os, random
import numpy as np
os.chdir(os.path.expanduser("~/receipts/data"))
os.makedirs("f2", exist_ok=True)
apps = sorted({r["app"] for r in map(json.loads, open("android_fm-rk-choice-obj.jsonl")) if r["bound"] is not None and r["truth_lo"] == r["truth_hi"]})
dev = sorted(random.Random(20261016).sample(apps, round(0.3 * len(apps))))
recs = {(r["cls"], r["sig"]): r for r in map(json.loads, open("holes_android_fw.jsonl")) if r["atoms"]}
meth = set()
for a in dev:
    z = np.load("graphs/%s.npz" % a)
    if "hole_cls" in z.files:
        meth |= {k for k in zip(z["hole_cls"].tolist(), z["hole_sub"].tolist()) if k in recs and recs[k]["source"] in ("none", "gap")}
meth = sorted(meth)
open("f2/dev_apps.txt", "w").write("".join(a + "\n" for a in dev))
open("f2/dev_methods.tsv", "w").write("".join("%s\t%s\n" % k for k in meth))
test = sorted(random.Random(20261016).sample(meth, 30))
with open("f2_test30.jsonl", "w") as f:
    for k in test:
        f.write(json.dumps(recs[k]) + "\n")
print("main apps %d, dev apps %d, dev methods %d, test 30 written" % (len(apps), len(dev), len(meth)))
