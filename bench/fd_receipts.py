"""Receipts on FlowDroid itself (paper: removing the "toy analysis" objection).

Usage: fd_receipts.py LIST SOURCES_SINKS OUT_DIR [MAX_SINKS]
  LIST: lines "name TAB apk path" (relative to the repository root)
FlowDroid reads library behavior from summary files, so holes need no change to FlowDroid:
  base   FlowDroid's own summaries (data/stubdroid): FlowDroid as it is used
  on     base plus every candidate flow of every framework method FlowDroid does not model (the holes; same methods and
         candidate flows as our analysis, data/holes_android_fw.jsonl, so every price file applies unchanged)
  truth  base plus the flows the main answer key says are real
A sink reported in "on" but not in "base" depends on holes. Its receipt: the hole methods on its reported paths are switched
off (all their candidate flows) and FlowDroid is run again; while the sink is still reported, the hole methods on its new
paths are added. The final set is a cut that FlowDroid itself has confirmed (the sink is no longer reported with it off).
A sink whose receipt cannot be confirmed within MAX_ITERS runs gets no bound (it is never cleared). Output per app:
OUT_DIR/<name>.json with the sinks of each kind and, per hole-dependent sink, the receipt (list of [cls, sig]), whether it
was confirmed, and whether the truth run reports the sink.
"""
import json, os, re, shutil, subprocess, sys, time, html
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
sys.path.insert(0, os.path.join(ROOT, "probes"))
from evaluate import labelled_holes
from make_summaries import method_xml

JAVA = os.path.expanduser("~/jdk/jdk-21.0.12.1+1/bin/java")
WORK = os.path.join(ROOT, "data/fd_receipts_work")
MAX_ITERS = 4
RUN_TIMEOUT = int(os.environ.get("FD_TIMEOUT", "1200"))


def write_dir(out, extra):
    """Summary directory: FlowDroid's own summaries plus extra[(cls, sig)] = [(src, tgt), ...] (only methods with flows)."""
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(ROOT, "data/stubdroid"), out)
    by_cls = {}
    for (cls, sig), flows in extra.items():
        if flows:
            by_cls.setdefault(cls, []).append(method_xml(sig, flows))
    for cls, methods in by_cls.items():
        path = os.path.join(out, cls.replace("$", "%24") + ".xml")
        body = "\n".join(methods)
        if os.path.exists(path):
            s = open(path).read()
            s = s.replace("<methods>", "<methods>\n" + body, 1) if "<methods>" in s else \
                s.replace("</summary>", "\t<methods>\n%s\n\t</methods>\n</summary>" % body, 1)
        else:
            s = '<?xml version="1.0" encoding="UTF-8"?>\n<summary fileFormatVersion="101">\n\t<methods>\n%s\n\t</methods>\n</summary>\n' % body
        open(path, "w").write(s)


def run_fd(apk, ss, sumdir, tag):
    os.makedirs(os.path.join(WORK, "runs"), exist_ok=True)
    xmlp = os.path.join(WORK, "runs", tag + ".xml")
    logp = os.path.join(WORK, "runs", tag + ".log")
    for p in (xmlp, logp):
        if os.path.exists(p):
            os.remove(p)
    with open(logp, "w") as lf:
        try:
            subprocess.run(["timeout", str(RUN_TIMEOUT), JAVA, "-Xmx10g", "-XX:ActiveProcessorCount=3", "-cp", os.path.join(ROOT, "tools/flowdroid/lib/*"),
                            "soot.jimple.infoflow.cmd.MainClass", "-a", apk, "-p", os.path.join(ROOT, "tools/flowdroid/platforms"),
                            "-s", ss, "-tw", "STUBDROID", "-t", sumdir, "-o", xmlp, "-cp", "-dt", str(RUN_TIMEOUT - 120), "-mt", "3"],
                           stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT)
        except Exception:
            return None
    if os.path.exists(xmlp) and os.path.getsize(xmlp) > 0:
        root = ET.parse(xmlp).getroot()
        if root.get("TerminationState") not in ("Success", None):
            return None
        res = {}
        for r in root.iter("Result"):
            sk = r.find("Sink")
            key = html.unescape(sk.get("Method")) + " | " + html.unescape(sk.get("Statement"))
            calls = res.setdefault(key, set())
            pes = list(r.iter("PathElement"))
            for pe in pes[1:-1]:  # the first and last elements are the source and the sink call themselves
                m = re.search(r"<([^:>]+): ([^>]+)>", html.unescape(pe.get("Statement", "")))
                if m:
                    calls.add((m.group(1), m.group(2)))
        return res
    if "Found 0 leaks" in open(logp, errors="replace").read():
        return {}
    return None


def main():
    lst, ss, outdir = sys.argv[1:4]
    max_sinks = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    os.makedirs(outdir, exist_ok=True)
    holes = labelled_holes()
    unmod = {k: h for k, h in holes.items() if h["source"] in ("none", "silver") and h["atoms"]}
    by_sub = {}
    for c, sub in unmod:
        by_sub.setdefault(sub, set()).add((c, sub))

    def holes_of(calls):
        """Hole methods behind the library calls on a path. A call written against an app class (this.getSystemService in
        an Activity) reaches the framework method by inheritance, as FlowDroid's summary lookup does; we map it to every
        unmodeled framework method with that sub-signature (a larger cut: valid, only looser)."""
        out = set()
        for c, sub in calls:
            out |= {(c, sub)} if (c, sub) in unmod else by_sub.get(sub, set())
        return out
    all_flows = {k: [(a["src"], a["tgt"]) for a in h["atoms"]] for k, h in unmod.items()}
    true_flows = {k: [(a["src"], a["tgt"]) for a in h["atoms"] if a["label"] is True] for k, h in unmod.items()}
    d_on, d_truth = os.path.join(WORK, "sum_on"), os.path.join(WORK, "sum_truth")
    if not os.path.exists(d_on + ".done"):
        write_dir(d_on, all_flows); open(d_on + ".done", "w").close()
    if not os.path.exists(d_truth + ".done"):
        write_dir(d_truth, true_flows); open(d_truth + ".done", "w").close()
    for line in open(os.path.join(ROOT, lst)).read().splitlines():
        if "\t" not in line:
            continue
        name, apk = line.split("\t")[:2]
        apk = apk if apk.startswith("/") else os.path.join(ROOT, apk)
        outp = os.path.join(outdir, name + ".json")
        if os.path.exists(outp):
            continue
        t0 = time.time()
        rec = {"app": name}
        base = run_fd(apk, ss, os.path.join(ROOT, "data/stubdroid"), name + ".base")
        on = run_fd(apk, ss, d_on, name + ".on") if base is not None else None
        truth = run_fd(apk, ss, d_truth, name + ".truth") if on is not None else None
        if base is None or on is None or truth is None:
            rec["status"] = "failed"
            json.dump(rec, open(outp, "w"))
            print(name, "failed", flush=True)
            continue
        hd = [s for s in on if s not in base]
        rec.update(status="ok", base=sorted(base), on_only=hd, truth=sorted(truth), sinks={})
        for i, s in enumerate(hd[:max_sinks]):
            cut = holes_of(on[s])
            confirmed = False
            for it in range(MAX_ITERS):
                if not cut:
                    break
                d = os.path.join(WORK, "sum_cut_" + name)
                write_dir(d, {k: v for k, v in all_flows.items() if k not in cut})
                res = run_fd(apk, ss, d, "%s.cut%d_%d" % (name, i, it))
                if res is None:
                    break
                if s not in res:
                    confirmed = True
                    break
                new = holes_of(res[s]) - cut
                if not new:
                    break
                cut |= new
            rec["sinks"][s] = {"receipt": sorted(cut), "confirmed": confirmed, "truth": s in truth}
        rec["seconds"] = round(time.time() - t0)
        json.dump(rec, open(outp, "w"))
        print(name, "base", len(base), "hole-dependent", len(hd), "confirmed", sum(v["confirmed"] for v in rec["sinks"].values()),
              "seconds", rec["seconds"], flush=True)


if __name__ == "__main__":
    main()
