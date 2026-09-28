"""Run the Soot fact extractor over every APK in bench/apks/pick.txt (in parallel)."""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(line):
    pkg, apk = line.split("\t")
    prefix = ""  # all code shipped in the APK (app + bundled libraries); android.jar stays library
    out = os.path.join(ROOT, "facts_apk_all", pkg)
    p = subprocess.run(["java", "-Xmx6g", "-cp", os.path.join(ROOT, "tools/soot-4.6.0-jar-with-dependencies.jar"),
                        os.path.join(ROOT, "extract/Facts.java"), os.path.join(ROOT, "bench/apks", apk),
                        os.path.join(ROOT, "tools/android/android.jar"), prefix, out],
                       capture_output=True, text=True)
    calls = os.path.join(out, "Call.facts")
    n = sum(1 for _ in open(calls)) if os.path.exists(calls) else 0
    return "%s rc=%d calls=%d %s" % (pkg, p.returncode, n, p.stderr.strip().splitlines()[-1][:120] if p.returncode else "")


with ThreadPoolExecutor(3) as ex:
    for r in ex.map(run, [l for f in sys.argv[1:] or ["pick.txt"] for l in open(os.path.join(ROOT, "bench/apks", f)).read().split("\n") if l]):
        print(r, flush=True)
