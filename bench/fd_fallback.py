"""FlowDroid counterpart of our step-e fallback (F1): FlowDroid with bundled libraries excluded (bench/FDExclude.java,
prefixes data/bundled_libs.txt, the app's own package kept), with the same budget rule as ours.

Usage: python3 bench/fd_fallback.py OUT.jsonl   (env as bench/fd_budget.py: FDB_XMX, FDB_JOBS, FDB_THREADS)
Two kinds of runs, from data/fd_budget.jsonl (the same-budget base runs):
  fallback  base run out of memory with more than 60 s of its 2100 s left: rerun with only the time left, as our
            fallback (bench/queues/f1e_fallback.sh); timeouts used the whole budget and get no second run, as ours
  control   base run succeeded with at least one sink: rerun with the full 2100 s, to count the leaks (distinct sink
            statements) that excluding the libraries loses without any notice
"""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fd_budget import ROOT, JAVA, XMX, JOBS, THREADS, SS, SUMS, get_apk

RUNS = os.path.join(ROOT, "data/fd_fallback_runs")
BASE_RUNS = os.path.join(ROOT, "data/fd_budget_runs")
LIBS = os.path.join(ROOT, "data/bundled_libs.txt")
CP = os.path.join(ROOT, "tools/fdexclude") + ":" + os.path.join(ROOT, "tools/flowdroid/lib/*")


def sinks(xmlp):
    if not (os.path.exists(xmlp) and os.path.getsize(xmlp) > 0):
        return None
    try:
        return sorted({r.find("Sink").get("Statement") for r in ET.parse(xmlp).getroot().iter("Result")})
    except ET.ParseError:
        return None


def run_fdx(apk, app, timeout):
    xmlp, logp = os.path.join(RUNS, app + ".xml"), os.path.join(RUNS, app + ".log")
    t0 = time.time()
    env = dict(os.environ, EXCLUDE_PREFIXES=LIBS, KEEP_PREFIX=app)
    with open(logp, "w") as lf:
        p = subprocess.run(["timeout", str(timeout), JAVA, "-Xmx" + XMX, "-XX:ActiveProcessorCount=" + THREADS, "-cp", CP,
                            "FDExclude", "-a", apk, "-p", os.path.join(ROOT, "tools/flowdroid/platforms"), "-s", SS,
                            "-tw", "STUBDROID", "-t", SUMS["base"], "-o", xmlp, "-dt", str(max(30, timeout - 120)),
                            "-mt", THREADS], stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    secs = round(time.time() - t0)
    log = open(logp, errors="replace").read()
    state = None
    if os.path.exists(xmlp) and os.path.getsize(xmlp) > 0:
        try:
            state = ET.parse(xmlp).getroot().get("TerminationState") or "Success"
        except ET.ParseError:
            state = "BadXML"
    if state is None:
        state = ("Timeout" if p.returncode == 124 else "OutOfMemory" if "OutOfMemoryError" in log
                 else "Success" if "Found 0 leaks" in log else "Error")
    return {"state": state, "seconds": secs, "sinks": sinks(xmlp) if state == "Success" else None}


def main():
    out = sys.argv[1]
    os.makedirs(RUNS, exist_ok=True)
    todo = []
    for d in map(json.loads, open(os.path.join(ROOT, "data/fd_budget.jsonl"))):
        b = d["base"]
        if b["state"] in ("DataFlowOutOfMemory", "OutOfMemory") and 2100 - b["seconds"] > 60:
            todo.append(("fallback", d, 2100 - b["seconds"]))
        elif b["state"] == "Success" and b.get("sinks"):
            todo.append(("control", d, 2100))
    todo.sort(key=lambda t: t[0] != "fallback")  # the fallback runs first
    done = {json.loads(l)["app"] for l in open(out)} if os.path.exists(out) else set()
    todo = [t for t in todo if t[1]["app"] not in done]
    print("%d runs to do" % len(todo), flush=True)

    def one(t):
        kind, d, budget = t
        apk, used = get_apk(d["app"], d["apk"])
        rec = {"app": d["app"], "kind": kind, "budget": budget, "apk": used, "base": d["base"]}
        if apk is None:
            rec["fdx"] = {"state": "NoAPK"}
            return rec
        rec["fdx"] = run_fdx(apk, d["app"], budget)
        if kind == "control":
            rec["base_sinks"] = sinks(os.path.join(BASE_RUNS, d["app"] + ".base.xml"))
        return rec

    with ThreadPoolExecutor(JOBS) as ex, open(out, "a") as fo:
        for rec in ex.map(one, todo):
            fo.write(json.dumps(rec) + "\n")
            fo.flush()
            print(rec["app"], rec["kind"], rec["base"]["state"], rec["fdx"]["state"], rec["fdx"].get("seconds"), flush=True)


if __name__ == "__main__":
    main()
