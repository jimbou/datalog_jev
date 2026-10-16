"""F3: fix the IzzyOnDroid app list before any run (REMAINING_WORK.md F3), with the criteria of the F-Droid corpus
(bench/scale.py: INTERNET plus a sensitive permission, APK 150 KB - 6 MB, minSdk <= 28), excluding every package that
is also in the F-Droid repository, newest version of each app, seeded draw of N (default 300, seed 20261016).
Writes data/f3/izzy_picks.tsv (package, APK name, SHA-256 from the index) and data/f3/izzy_selection.txt (index
timestamp, counts). Usage: izzy_select.py [N]
"""
import json, os, random, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
from scale import SENS
IZZY = "https://apt.izzysoft.de/fdroid/repo"
OUT = os.path.join(ROOT, "data/f3")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def get(url, path):
    if not os.path.exists(path):
        subprocess.run(["curl", "-sfL", "--retry", "5", "-o", path, url], check=True)
    return json.load(open(path))


os.makedirs(OUT, exist_ok=True)
izzy = get(IZZY + "/index-v1.json", os.path.join(OUT, "izzy-index-v1.json"))
fdroid = set(get("https://mirrors.tuna.tsinghua.edu.cn/fdroid/repo/index-v1.json", os.path.join(OUT, "fdroid-index-v1.json"))["packages"])
elig = []
for pkg, vs in izzy["packages"].items():
    v = vs[0]
    perms = {p[0].split(".")[-1] for p in v.get("uses-permission", []) if p}
    if pkg in fdroid or "INTERNET" not in perms or not perms & SENS:
        continue
    if not 150_000 < v["size"] < 6_000_000 or int(v.get("minSdkVersion") or 0) > 28:
        continue
    elig.append((pkg, v["apkName"], v.get("hash", "")))
elig.sort()
random.Random(20261016).shuffle(elig)
pick = elig[:N]
with open(os.path.join(OUT, "izzy_picks.tsv"), "w") as f:
    for r in pick:
        f.write("\t".join(r) + "\n")
ts = izzy.get("repo", {}).get("timestamp", 0)
info = ("IzzyOnDroid index timestamp %s (%d ms); packages %d; also in F-Droid excluded; eligible %d; picked %d (seed 20261016)\n"
        % (time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(ts / 1000)), ts, len(izzy["packages"]), len(elig), len(pick)))
open(os.path.join(OUT, "izzy_selection.txt"), "w").write(info)
print(info, end="")
