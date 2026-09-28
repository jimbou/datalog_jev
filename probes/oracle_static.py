"""Oracle 1 of the closing loop: a static check on the real library code.

For each hole method, extract its body and callees from android-all (framework) and the JDK
(java.*) up to a call depth (extract/LibFacts.java), run analysis/lib.dl, and classify every
atom of the method:
  flow      the over-approximate analysis finds a path (the flow may exist)
  no-flow   no path, and no tainted value reaches a frontier call: the flow is absent up to the
            extraction bounds
  unknown   no path found, but taint reaches a native / abstract / too-deep call, or the method
            has no body (interface, native)
Usage: oracle_static.py KEYS_TSV [DEPTH]      (KEYS_TSV: class TAB subsignature per line)
Writes data/oracle_static.jsonl: {cls, sig, labels: [flow|no-flow|unknown per atom]}.
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.environ.get("SCRATCH_DIR", tempfile.gettempdir())
CP = os.path.join(ROOT, "tools/soot-4.6.0-jar-with-dependencies.jar") + ":" + os.path.join(ROOT, "tools/extract-classes")
LIBCP = os.path.join(ROOT, "tools/witness/android-all-13-robolectric-9030017.jar") + ":VIRTUAL_FS_FOR_JDK"


def rows(d, rel, ext=".csv"):
    p = os.path.join(d, rel + ext)
    return [l.rstrip("\n").split("\t") for l in open(p, newline="\n")] if os.path.exists(p) else []


def classify(keys, holes, depth):
    with tempfile.TemporaryDirectory(prefix="oracle1-", dir=SCRATCH) as d:
        facts, out = os.path.join(d, "facts"), os.path.join(d, "out")
        os.makedirs(out)
        tsv = os.path.join(d, "targets.tsv")
        open(tsv, "w").write("".join("%s\t%s\n" % k for k in keys))
        subprocess.run(["java", "-Xmx8g", "-cp", CP, "LibFacts", LIBCP, tsv, str(depth), facts],
                       check=True, capture_output=True, text=True)
        subprocess.run([os.path.join(ROOT, "tools/souffle.sh"), "-j", "8", "-F", facts, "-D", out,
                        os.path.join(ROOT, "analysis/lib.dl")], check=True, capture_output=True, text=True)
        alias = {a: b for a, b in rows(facts, "RootAlias", ".facts")}
        nobody = {r[0] for r in rows(facts, "RootNoBody", ".facts")}
        flow = {tuple(r) for r in rows(out, "Flow")}
        unknown = {tuple(r) for r in rows(out, "Unknown")}
    res = []
    for cls, sub in keys:
        sig = "<%s: %s>" % (cls, sub)
        impl = alias.get(sig, sig)
        labels = []
        for a in holes[(cls, sub)]["atoms"]:
            if sig in nobody:
                labels.append("unknown")
            elif (impl, a["src"], a["tgt"]) in flow:
                labels.append("flow")
            elif (impl, a["src"]) in unknown:
                labels.append("unknown")
            else:
                labels.append("no-flow")
        res.append({"cls": cls, "sig": sub, "labels": labels})
    return res


def main():
    keys = [tuple(l.rstrip("\n").split("\t")) for l in open(sys.argv[1]) if l.strip()]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    holes = {(h["cls"], h["sig"]): h for h in map(json.loads, open(os.path.join(ROOT, "data/holes_android_fw.jsonl")))}
    keys = [k for k in keys if k in holes]
    out_path = os.path.join(ROOT, "data/oracle_static.jsonl")
    done = {(d["cls"], d["sig"]) for d in map(json.loads, open(out_path))} if os.path.exists(out_path) else set()
    keys = [k for k in keys if k not in done]
    counts = {}
    with open(out_path, "a") as f:
        for i in range(0, len(keys), 200):  # batches keep each Soufflé run small
            for r in classify(keys[i:i + 200], holes, depth):
                f.write(json.dumps(r) + "\n")
                for l in r["labels"]:
                    counts[l] = counts.get(l, 0) + 1
            print("classified %d/%d methods %s" % (min(i + 200, len(keys)), len(keys), counts), flush=True)


if __name__ == "__main__":
    main()
