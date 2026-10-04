"""Pick the apps for the FlowDroid validation and write data/flowdroid/apps.tsv (package TAB apk file).

Usage: flowdroid_select.py [N] [MAX_APK_MB]      (default 40 apps, APKs up to 8 MB)
Candidates are the apps that have an APK in bench/apks (listed in bench/apks/pick*.txt), that our evaluation covers with at least one
hole-dependent sink (data/android_choice-obj.jsonl), and whose APK is small enough for FlowDroid to finish in reasonable time.
A fixed seed makes the choice reproducible.
"""
import glob, json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    mb = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    apk = {}
    for pick in glob.glob(os.path.join(ROOT, "bench/apks/pick*.txt")):
        for line in open(pick).read().split("\n"):
            if line.count("\t") == 1 and "\x00" not in line:
                pkg, f = line.split("\t")
                if os.path.exists(os.path.join(ROOT, "bench/apks", f)):
                    apk[pkg] = f
    covered = set()
    for l in open(os.path.join(ROOT, "data/android_choice-obj.jsonl")):
        r = json.loads(l)
        if r["bound"] is not None:
            covered.add(r["app"])
    cands = sorted(p for p in apk if p in covered and os.path.getsize(os.path.join(ROOT, "bench/apks", apk[p])) <= mb * 1e6)
    random.Random(20261004).shuffle(cands)
    pick = cands[:n]
    os.makedirs(os.path.join(ROOT, "data/flowdroid"), exist_ok=True)
    with open(os.path.join(ROOT, "data/flowdroid/apps.tsv"), "w") as f:
        for p in pick:
            f.write("%s\t%s\n" % (p, apk[p]))
    print("candidates:", len(cands), "| with an APK:", len(apk), "| covered by the evaluation:", len(covered & set(apk)), "| picked:", len(pick))


if __name__ == "__main__":
    main()
