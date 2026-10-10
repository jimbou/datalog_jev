"""Same-budget comparison: FlowDroid on every picked F-Droid app, with the time and memory our graph build had.

Usage: python3 bench/fd_budget.py OUT.jsonl   (env: FDB_TIMEOUT=2100, FDB_XMX=16g, FDB_JOBS=3, FDB_THREADS=3, FDROID_BASE)

Our build per app: Soot extraction (1200 s) + Souffle (900 s, 16 GB address space), two apps in parallel. FlowDroid gets
2100 s and a 16 GB heap per run, three runs of 3 threads in parallel on the 8 cores. Two runs per app: FlowDroid with its models (base), and with every
unmodeled method of our hole file opened as an all-flows summary (holes; skipped when the base run fails). APKs deleted after a failed build of ours are
downloaded again from the F-Droid mirror; if the picked version is gone, the current one is used and recorded.
Our outcome per app comes from data/graphs (built) and data/android_failed.txt (over the limits).
"""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVA = os.path.expanduser("~/jdk/jdk-21.0.12.1+1/bin/java")
TIMEOUT = int(os.environ.get("FDB_TIMEOUT", "2100"))
XMX = os.environ.get("FDB_XMX", "16g")
JOBS = int(os.environ.get("FDB_JOBS", "3"))
THREADS = os.environ.get("FDB_THREADS", "3")
FDROID = os.environ.get("FDROID_BASE", "https://mirrors.tuna.tsinghua.edu.cn/fdroid/repo")
APKS = os.path.join(ROOT, "bench/apks")
DL = os.path.join(ROOT, "data/fd_budget_apks")
RUNS = os.path.join(ROOT, "data/fd_budget_runs")
SS = os.path.join(ROOT, "data/SourcesAndSinks.txt")
SUMS = {"base": os.path.join(ROOT, "data/stubdroid"), "holes": os.path.join(ROOT, "data/fd_receipts_work/sum_on")}


def fetch(url, path):
    part = path + ".part"
    r = subprocess.run(["curl", "-sfL", "--retry", "5", "--retry-all-errors", "-C", "-", "-o", part, url])
    if r.returncode == 0:
        os.replace(part, path)
        return True
    return False


def current_apk(pkg, index={}):
    if not index:
        p = os.path.join(DL, "index-v1.json")
        if not os.path.exists(p):
            fetch(FDROID + "/index-v1.json", p)
        index.update(json.load(open(p))["packages"])
    vs = index.get(pkg)
    return vs[0]["apkName"] if vs else None


def get_apk(pkg, name):
    for d in (APKS, DL):
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name), name
    if fetch("%s/%s" % (FDROID, name), os.path.join(DL, name)):
        return os.path.join(DL, name), name
    cur = current_apk(pkg)
    if cur and (os.path.exists(os.path.join(DL, cur)) or fetch("%s/%s" % (FDROID, cur), os.path.join(DL, cur))):
        return os.path.join(DL, cur), cur
    return None, None


def run_fd(apk, tag, kind):
    xmlp, logp = os.path.join(RUNS, tag + "." + kind + ".xml"), os.path.join(RUNS, tag + "." + kind + ".log")
    t0 = time.time()
    with open(logp, "w") as lf:
        p = subprocess.run(["timeout", str(TIMEOUT), JAVA, "-Xmx" + XMX, "-XX:ActiveProcessorCount=" + THREADS,
                            "-cp", os.path.join(ROOT, "tools/flowdroid/lib/*"), "soot.jimple.infoflow.cmd.MainClass",
                            "-a", apk, "-p", os.path.join(ROOT, "tools/flowdroid/platforms"), "-s", SS,
                            "-tw", "STUBDROID", "-t", SUMS[kind], "-o", xmlp, "-dt", str(TIMEOUT - 120), "-mt", THREADS],
                           stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT)
    secs = round(time.time() - t0)
    log = open(logp, errors="replace").read()
    state, leaks = None, None
    if os.path.exists(xmlp) and os.path.getsize(xmlp) > 0:
        try:
            root = ET.parse(xmlp).getroot()
            state = root.get("TerminationState") or "Success"
            leaks = len({r.find("Sink").get("Statement") for r in root.iter("Result")})
        except ET.ParseError:
            state = "BadXML"
    if state is None:
        if p.returncode == 124:
            state = "Timeout"
        elif "OutOfMemoryError" in log:
            state = "OutOfMemory"
        elif "Found 0 leaks" in log:
            state, leaks = "Success", 0
        else:
            state = "Error"
    return {"state": state, "seconds": secs, "sinks": leaks}


def main():
    out = sys.argv[1]
    os.makedirs(DL, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)
    picks = {}
    for f in sorted(os.listdir(APKS)):
        if f.startswith("pick") and f.endswith(".txt"):
            for l in open(os.path.join(APKS, f)).read().splitlines():
                if "\t" in l:
                    pkg, name = l.split("\t")[:2]
                    picks.setdefault(pkg, name)
    built = {f[:-4] for f in os.listdir(os.path.join(ROOT, "data/graphs")) if f.endswith(".npz")}
    failed = set(open(os.path.join(ROOT, "data/android_failed.txt")).read().split())
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["app"] for l in open(out) if l.strip()}
    todo = [(p, n) for p, n in sorted(picks.items()) if p not in done]
    print("%d picked apps, %d done, %d to run" % (len(picks), len(done), len(todo)), flush=True)

    def one(item):
        pkg, name = item
        rec = {"app": pkg, "ours": "built" if pkg in built else "failed" if pkg in failed else "unknown", "picked_apk": name}
        apk, used = get_apk(pkg, name)
        rec["apk"] = used
        if apk is None:
            rec["base"] = rec["holes"] = {"state": "NoAPK"}
            return rec
        rec["base"] = run_fd(apk, pkg, "base")
        # the run with holes open does strictly more work, so it is skipped when the base run already fails the budget
        rec["holes"] = run_fd(apk, pkg, "holes") if rec["base"]["state"] == "Success" else {"state": "Skipped"}
        return rec

    with ThreadPoolExecutor(JOBS) as ex, open(out, "a") as fo:
        for rec in ex.map(one, todo):
            fo.write(json.dumps(rec) + "\n")
            fo.flush()
            print(rec["app"], rec["ours"], rec["base"]["state"], rec["holes"]["state"], flush=True)


if __name__ == "__main__":
    main()
