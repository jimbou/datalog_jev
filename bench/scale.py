"""Grow the app corpus in batches without keeping extracted facts.

Picks F-Droid apps (internet access plus a sensitive permission, 150 KB - 6 MB, minSdk <= 28) not
yet in bench/apks/pick*.txt, and for each batch: downloads the APKs, appends them to PICK, and
builds their graphs with analysis/run_android.py (facts are extracted into a temporary directory
and deleted). Stops early when free disk space falls below MIN_FREE_GB.

Usage: scale.py TOTAL [BATCH] [PICK]      (env: SCRATCH_DIR, JOBS, MIN_FREE_GB)
"""
import json, os, random, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APKS = os.path.join(ROOT, "bench/apks")
SCRATCH = os.environ.get("SCRATCH_DIR", tempfile.gettempdir())
MIN_FREE_GB = float(os.environ.get("MIN_FREE_GB", "20"))
SENS = {"ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "READ_PHONE_STATE", "READ_CONTACTS", "READ_SMS",
        "READ_CALL_LOG", "GET_ACCOUNTS", "RECORD_AUDIO", "ACCESS_WIFI_STATE", "READ_CALENDAR", "CAMERA",
        "READ_EXTERNAL_STORAGE", "BLUETOOTH", "ACCESS_NETWORK_STATE"}


def free_gb():
    return shutil.disk_usage(ROOT).free / 2 ** 30


def fetch(url, path):
    """Download with retries and resume; the file appears only once complete."""
    part = path + ".part"
    r = subprocess.run(["curl", "-sfL", "--retry", "5", "--retry-all-errors", "-C", "-", "-o", part, url])
    if r.returncode == 0:
        os.replace(part, path)
        return True
    return False


def candidates():
    index = os.path.join(SCRATCH, "fdroid-index-v1.json")
    if not os.path.exists(index) and not fetch("https://f-droid.org/repo/index-v1.json", index):
        sys.exit("could not download the F-Droid index")
    have = set()
    for f in os.listdir(APKS):
        if f.startswith("pick") and f.endswith(".txt"):
            have |= {l.split("\t")[0] for l in open(os.path.join(APKS, f)).read().split("\n") if l}
    out = []
    for pkg, vs in json.load(open(index))["packages"].items():
        v = vs[0]
        perms = {p[0].split(".")[-1] for p in v.get("uses-permission", []) if p}
        if pkg in have or "INTERNET" not in perms or not perms & SENS:
            continue
        if not 150_000 < v["size"] < 6_000_000 or int(v.get("minSdkVersion") or 0) > 28:
            continue
        out.append((pkg, v["apkName"]))
    random.Random(3).shuffle(out)
    return out


def main():
    total = int(sys.argv[1])
    batch = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    pick = os.path.join(APKS, sys.argv[3] if len(sys.argv) > 3 else "pick3.txt")
    todo = candidates()[:total]
    print("eligible apps picked: %d" % len(todo), flush=True)
    for i in range(0, len(todo), batch):
        if free_gb() < MIN_FREE_GB:
            print("stopping: %.1f GB free < %.0f GB" % (free_gb(), MIN_FREE_GB), flush=True)
            break
        got = []
        for pkg, apk in todo[i:i + batch]:
            if fetch("https://f-droid.org/repo/" + apk, os.path.join(APKS, apk)):
                got.append((pkg, apk))
            else:
                print("download failed:", pkg, flush=True)
        with open(pick, "a") as f:
            for pkg, apk in got:
                f.write("%s\t%s\n" % (pkg, apk))
        subprocess.run([sys.executable, os.path.join(ROOT, "analysis/run_android.py")], check=False)
        print("batch %d done: %d apps, %.1f GB free" % (i // batch + 1, len(got), free_gb()), flush=True)


if __name__ == "__main__":
    main()
