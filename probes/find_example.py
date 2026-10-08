"""Find motivating-example candidates: two one-fact receipts in the same app's own code, one real (high price) and one
leak-free (low price), whose sink calls are Android APIs (not java.* entries such as String.replace).

Usage: find_example.py RESULTS [MAX_APPS]     (run on the server; extracts facts for candidate apps into /tmp/fx_<app>)
"""
import collections, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVA = os.path.expanduser("~/jdk/jdk-21.0.12.1+1/bin/java")


def apk_of():
    out = {}
    for f in os.listdir(os.path.join(ROOT, "bench/apks")):
        if f.startswith("pick") and f.endswith(".txt"):
            for line in open(os.path.join(ROOT, "bench/apks", f)).read().splitlines():
                if line.count("\t") == 1:
                    pkg, apk = line.split("\t")
                    out[pkg] = os.path.join(ROOT, "bench/apks", apk)
    return out


def callees(app, apk):
    d = "/tmp/fx_" + app
    if not os.path.exists(os.path.join(d, "Call.facts")):
        os.makedirs(d, exist_ok=True)
        subprocess.run([JAVA, "-Xmx6g", "-cp", os.path.join(ROOT, "tools/soot-4.6.0-jar-with-dependencies.jar"),
                        os.path.join(ROOT, "extract/Facts.java"), apk, os.path.join(ROOT, "tools/android/android.jar"), "", d],
                       capture_output=True, timeout=1200)
    m = {}
    for l in open(os.path.join(d, "Call.facts")):
        f = l.rstrip("\n").split("\t")
        m[f[0]] = f[3] + ": " + f[4]
    return m


def main():
    res = sys.argv[1]
    max_apps = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    by_app = collections.defaultdict(list)
    for l in open(os.path.join(ROOT, res)):
        r = json.loads(l)
        if r["bound"] is None or r["truth_lo"] != r["truth_hi"] or len(r["cut"]) != 1:
            continue
        cls = r["site"][1:].split(":")[0]
        if not cls.startswith(".".join(r["app"].split(".")[:2])):
            continue
        by_app[r["app"]].append(r)
    cands = []
    for app, rs in by_app.items():
        real = [r for r in rs if r["truth_lo"] and r["cut"][0]["p"] >= 0.6]
        safe = [r for r in rs if not r["truth_lo"] and r["cut"][0]["p"] <= 0.1]
        if real and safe:
            cands.append((app, real, safe))
    apks = apk_of()
    cands = [c for c in cands if c[0] in apks][:max_apps]

    def check(c):
        app, real, safe = c
        try:
            m = callees(app, apks[app])
        except Exception as e:
            return app, None, str(e)
        good = lambda r: m.get(r["site"], "").startswith("android.")
        return app, ([(r["site"], m.get(r["site"]), r["cut"][0]) for r in real if good(r)],
                     [(r["site"], m.get(r["site"]), r["cut"][0]) for r in safe if good(r)]), None
    with ThreadPoolExecutor(4) as ex:
        for app, found, err in ex.map(check, cands):
            if err or not found or not found[0] or not found[1]:
                continue
            print("==", app)
            for tag, lst in (("REAL", found[0][:3]), ("SAFE", found[1][:3])):
                for site, callee, f in lst:
                    print("  %s %s\n     sink %s | fact %s.%s %s->%s p=%.2f" % (tag, site, callee, f["cls"], f["sub"], f["src"], f["tgt"], f["p"]))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
