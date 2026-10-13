"""Build stage: run the Soufflé taint analysis on each extracted app and store its flow graph.

Usage: run_android.py [APP_GLOB]      (env: JOBS, SOUFFLE_MEM_GB, SCRATCH_DIR; F1 options below)
F1 options (REMAINING_WORK.md): TOTAL_TIMEOUT=2100 gives extraction and Soufflé one shared budget per app instead of
1200 + 900 s; SOUFFLE_BIN runs taint.dl compiled with `souffle -o` (checked against the md5 of TAINT_DL stored next to
it); SOUFFLE_THREADS (default 8); EXTRACT_XMX (default 6g) and EXTRACT_THREADS for the Soot JVM; REASONS_FILE records
per app the outcome, the failing stage and the seconds used. LIB_PREFIXES (F1 e, e.g. data/bundled_libs.txt): classes under
these package prefixes (except the app's own package) are not extracted and their methods become holes.
BUDGET_FILE (lines "app TAB seconds"): a per-app budget overriding TOTAL_TIMEOUT, e.g. the time a first attempt left.
For every app (stored facts in facts_apk_all/, or an APK listed in bench/apks/pick*.txt, whose
facts are extracted into a temporary directory and deleted afterwards), writes
data/graphs/<app>.npz holding the relevant subgraph
(nodes on some source -> sink path when every hole is on):
  code_u, code_v      code edges (never cut)
  cand_u, cand_mid    candidate hole edges, one per call site and atom
  cand_hole, cand_k   which hole method (index into hole_cls/hole_sub/hole_kind) and which atom
  n_sink_calls        sink call sites with a non-constant argument (for baseline B2)
  sink_site, sink_ptr, sink_nodes   sink call sites and their nodes (CSR layout)
  n, stats            node count (node 0 = SRC) and Soufflé statistics (JSON)
Soufflé writes to a temporary directory that is removed after each app, so only the graphs
are kept. Graphs do not depend on prices or labels; analysis/evaluate.py prices them.
"""
import fnmatch, glob, gzip, hashlib, json, os, re, resource, subprocess, sys, tempfile, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes"))
from build_libflow import menu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUFFLE = os.path.join(ROOT, "tools/souffle.sh")
GRAPHS = os.environ.get("GRAPHS_DIR") or os.path.join(ROOT, "data/graphs")
TAINT_DL = os.environ.get("TAINT_DL") or os.path.join(ROOT, "analysis/taint.dl")  # e.g. analysis/taint_entry.dl
APPS_FILE = os.environ.get("APPS_FILE")  # optional: only the packages listed (first column) in this file
SCRATCH = os.environ.get("SCRATCH_DIR", tempfile.gettempdir())
VALUE_TYPES = {"void", "int", "long", "short", "byte", "boolean", "char", "double", "float", "java.lang.String",
               "java.lang.Integer", "java.lang.Long", "java.lang.Short", "java.lang.Byte", "java.lang.Boolean",
               "java.lang.Character", "java.lang.Double", "java.lang.Float", "java.lang.CharSequence"}
SOUFFLE_TIMEOUT = 900
EXTRACT_TIMEOUT = 1200
TOTAL_TIMEOUT = int(os.environ.get("TOTAL_TIMEOUT", "0"))  # 0: the separate limits above
SOUFFLE_BIN = os.environ.get("SOUFFLE_BIN")
SOUFFLE_THREADS = os.environ.get("SOUFFLE_THREADS", "8")
EXTRACT_XMX = os.environ.get("EXTRACT_XMX", "6g")
EXTRACT_THREADS = os.environ.get("EXTRACT_THREADS")
REASONS_FILE = os.environ.get("REASONS_FILE")
# F1 e: bundled third-party libraries as library code (data/bundled_libs.txt): not extracted, their methods become holes
# per-app budget in seconds (file "app TAB seconds"): overrides TOTAL_TIMEOUT, e.g. the time left after a first attempt
BUDGETS = {a: int(s) for a, s in (l.split("\t")[:2] for l in open(os.environ["BUDGET_FILE"]) if "\t" in l)} \
    if os.environ.get("BUDGET_FILE") else {}
LIB_PREFIXES_FILE = os.environ.get("LIB_PREFIXES")
LIB_PREFIXES = tuple(l.strip() for l in open(LIB_PREFIXES_FILE) if l.strip() and not l.startswith("#")) if LIB_PREFIXES_FILE else ()
MAX_ATTEMPTS = 3  # an app that has crashed the run this many times is skipped
SOUFFLE_MEM = int(os.environ.get("SOUFFLE_MEM_GB", "12")) << 30
JOBS = int(os.environ.get("JOBS", "2"))


def framework_holes():
    """Framework methods with candidate atoms, keyed by (class, subsignature). Read from
    data/holes_android_fw.jsonl (the framework slice of holes_android.jsonl, extended by
    probes/extend_holes_fw.py) when it exists."""
    fw_path = os.path.join(ROOT, "data/holes_android_fw.jsonl")
    if os.path.exists(fw_path):
        return {(r["cls"], r["sig"]): r for r in map(json.loads, open(fw_path))}
    fw = {l.strip() for l in open(os.path.join(ROOT, "data/android_classes.txt"))}
    return {(r["cls"], r["sig"]): r for r in map(json.loads, open(os.path.join(ROOT, "data/holes_android.jsonl")))
            if r["atoms"] and r["cls"] in fw}


def framework_supers():
    cache = os.path.join(ROOT, "data/android_supers.tsv")
    if not os.path.exists(cache):
        classes = open(os.path.join(ROOT, "data/android_classes.txt")).read()
        out = subprocess.run(["java", "-cp", os.path.join(ROOT, "tools/android/android.jar"),
                              os.path.join(ROOT, "probes/Supers.java")], input=classes,
                             capture_output=True, text=True, check=True).stdout
        open(cache, "w").write(out)
    return {c: s.split(",") for c, s in (l.split("\t") for l in open(cache).read().splitlines())}


def sources_sinks():
    """FlowDroid's default SourcesAndSinks.txt: one entry per line; lines starting with % are
    disabled alternatives (e.g. the inter-component sources) and are skipped."""
    src, snk = set(), set()
    for line in open(os.environ.get("SOURCES_SINKS") or os.path.join(ROOT, "data/SourcesAndSinks.txt")):
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        m = re.match(r"(?:\S+\s+)?<([^:>]+): ([^>]+)>.*?->\s*(_[A-Z]+_)", line)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        if m.group(3) in ("_SOURCE_", "_BOTH_"):
            src.add(key)
        if m.group(3) in ("_SINK_", "_BOTH_"):
            snk.add(key)
    return src, snk


def called_methods(app_dir):
    """{(class, subsignature): kind} for every call in the app; kind as in probes/build_holes_android."""
    out = {}
    for l in open(os.path.join(app_dir, "Call.facts"), newline="\n"):
        p = l.rstrip("\n").split("\t")
        if len(p) == 7 and p[2] != "dynamic":
            out[(p[3], p[4])] = "ctor" if " <init>(" in p[4] else ("static" if p[2] == "static" else "instance")
    return out


def prepare(app_dir, fw, supers, src, snk):
    """Write the per-app inputs of taint.dl. Candidate atoms of every framework call come from the
    same menu as probes/build_holes_android.py, so atom indices match the hole records."""
    kinds = called_methods(app_dir)
    called = set(kinds)
    with open(os.path.join(app_dir, "HoleAtom.facts"), "w") as f:
        for (cls, sub), kind in kinds.items():
            if cls in fw or (LIB_PREFIXES and cls.startswith(LIB_PREFIXES)):
                for k, (s, t) in enumerate(menu({"sig": sub, "kind": kind})):
                    f.write("%s\t%s\t%d\t%s\t%s\n" % (cls, sub, k, s, t))
    with open(os.path.join(app_dir, "FwSuper.facts"), "w") as f:
        for c, ss in supers.items():
            for sup in ss:
                if sup and sup != c:
                    f.write("%s\t%s\n" % (c, sup))
    with open(os.path.join(app_dir, "SubRet.facts"), "w") as f:
        for sub in sorted({sub for _, sub in called}):
            f.write("%s\t%s\n" % (sub, sub.split(" ")[0]))
    with open(os.path.join(app_dir, "ValueSub.facts"), "w") as f:
        for sub in sorted({sub for _, sub in called if sub.split(" ")[0] in VALUE_TYPES}):
            f.write(sub + "\n")
    # the extractor writes a relation's file only when the app has a fact for it (e.g. no SStore.facts in an app without
    # static field writes), and Soufflé refuses to start on a missing input file: create the missing ones empty
    inputs = [r.strip() for l in open(TAINT_DL) if l.startswith(".input") for r in l[len(".input"):].split(",")]
    for name in inputs + ["Component", "IntentFilter"]:
        open(os.path.join(app_dir, name + ".facts"), "a").close()
    for name, table in (("SourceMethod", src), ("SinkMethod", snk)):
        with open(os.path.join(app_dir, name + ".facts"), "w") as f:
            for cls, sub in called:
                if any((c, sub) in table for c in supers.get(cls, [cls])):
                    f.write("%s\t%s\n" % (cls, sub))


def graph_path(app):
    return os.path.join(GRAPHS, app + ".npz")


def graph_ok(p):
    """The file is a complete graph (a zip cut short by a crash or reboot fails to open)."""
    try:
        z = np.load(p)
        return "n" in z.files and "sink_nodes" in z.files and int(z["n"]) > 0
    except Exception:
        return False


def graph_fresh(app):
    p = graph_path(app)
    return (os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(TAINT_DL)
            and graph_ok(p))


def rows(out, rel):
    """Rows of a Soufflé output relation (gzipped or plain); fields are tab-separated."""
    path = os.path.join(out, rel + ".csv")
    if os.path.exists(path + ".gz"):
        f = gzip.open(path + ".gz", "rt", newline="\n")
    elif os.path.exists(path):
        f = open(path, newline="\n")
    else:
        return []
    with f:
        return [l.rstrip("\n").split("\t") for l in f]


def run_souffle(app_dir, out, timeout=SOUFFLE_TIMEOUT):
    """None on success, else why Soufflé failed: timeout, memory (killed by a signal or out of address space), error."""
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (SOUFFLE_MEM, SOUFFLE_MEM))
    cmd = ([SOUFFLE_BIN] if SOUFFLE_BIN else [SOUFFLE]) + ["-j", SOUFFLE_THREADS, "-F", app_dir, "-D", out]
    if not SOUFFLE_BIN:
        cmd.append(TAINT_DL)
    if timeout <= 0:
        return "souffle timeout (no time left)"
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, preexec_fn=limit)
    except subprocess.TimeoutExpired:
        return "souffle timeout"
    if p.returncode == 0:
        return None
    err = (p.stderr or "").strip().splitlines()
    if p.returncode < 0 or "bad_alloc" in p.stderr or "memory" in p.stderr.lower():
        return "souffle memory (rc %d)" % p.returncode
    return "souffle error (rc %d: %s)" % (p.returncode, err[-1][:100] if err else "")


def sink_call_count(app_dir):
    """Sink call sites with at least one non-constant argument (denominator for baseline B2)."""
    sinks = {tuple(l.rstrip("\n").split("\t")) for l in open(os.path.join(app_dir, "SinkMethod.facts"), newline="\n")}
    var_arg = set()
    for l in open(os.path.join(app_dir, "Arg.facts"), newline="\n"):
        p = l.rstrip("\n").split("\t")
        if len(p) == 3 and p[2] != "-" and not p[2].startswith("str:"):
            var_arg.add(p[0])
    n = 0
    for l in open(os.path.join(app_dir, "Call.facts"), newline="\n"):
        p = l.rstrip("\n").split("\t")
        n += len(p) == 7 and (p[3], p[4]) in sinks and p[0] in var_arg
    return n


def save_graph(out, app, kinds=None, n_sink_calls=0):
    idx = {"SRC": 0}

    def node(n):
        if n not in idx:
            idx[n] = len(idx)
        return idx[n]

    code = [(node(a), node(b)) for a, b in rows(out, "RelEdge")]
    code += [(0, node(n)) for n, in rows(out, "RelSrc")]
    hole_id, cand = {}, []
    for mid, a, cls, sub, k in rows(out, "RelCand"):
        h = hole_id.setdefault((cls, sub), len(hole_id))
        cand.append((node(a), node(mid), h, int(k)))
    sinks = {}
    for site, n in rows(out, "RelSink"):
        sinks.setdefault(site, []).append(node(n))
    sites = sorted(sinks)
    ptr = np.cumsum([0] + [len(sinks[s]) for s in sites])
    hk = sorted(hole_id, key=hole_id.get)
    c = np.array(cand, dtype=np.int64).reshape(-1, 4)
    e = np.array(code, dtype=np.int32).reshape(-1, 2)
    tmp = graph_path(app) + ".tmp"  # write, sync, then rename: a crash never leaves a partial graph
    with open(tmp, "wb") as fh:
        np.savez_compressed(
        fh, n=len(idx),
        code_u=e[:, 0], code_v=e[:, 1],
        cand_u=c[:, 0].astype(np.int32), cand_mid=c[:, 1].astype(np.int32),
        cand_hole=c[:, 2].astype(np.int32), cand_k=c[:, 3].astype(np.int16),
        hole_cls=np.array([k[0] for k in hk]), hole_sub=np.array([k[1] for k in hk]),
        hole_kind=np.array([(kinds or {}).get(k, "") for k in hk]), n_sink_calls=n_sink_calls,
        sink_site=np.array(sites), sink_ptr=ptr.astype(np.int64),
        sink_nodes=np.array([n for s in sites for n in sinks[s]], dtype=np.int32),
        icc_sub=np.array([r[0] for r in rows(out, "IccLabel")]), icc_label=np.array([r[1] for r in rows(out, "IccLabel")]),
        icc_info=json.dumps([r for r in rows(out, "IccInfo")]),
        stats=json.dumps(dict((k, int(v)) for k, v in rows(out, "Stats"))))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, graph_path(app))


CTX = None


def extract(apk, out, timeout=EXTRACT_TIMEOUT, app=""):
    """Soot facts for one APK (all code shipped in it); returns True on success."""
    jvm = ["java", "-Xmx" + EXTRACT_XMX] + (["-XX:ActiveProcessorCount=" + EXTRACT_THREADS] if EXTRACT_THREADS else [])
    p = subprocess.run(jvm + ["-cp", os.path.join(ROOT, "tools/soot-4.6.0-jar-with-dependencies.jar"),
                        os.path.join(ROOT, "extract/Facts.java"), apk, os.path.join(ROOT, "tools/android/android.jar"),
                        "", out], capture_output=True, text=True, timeout=timeout,
                       env=dict(os.environ, EXCLUDE_PREFIXES=LIB_PREFIXES_FILE or "", KEEP_PREFIX=app if LIB_PREFIXES else ""))
    if p.returncode != 0 and "OutOfMemoryError" in (p.stderr or "") + (p.stdout or ""):
        extract.reason = "extract memory"
    else:
        extract.reason = "extract error (rc %d)" % p.returncode
    ok = p.returncode == 0 and os.path.exists(os.path.join(out, "Call.facts"))
    if ok and "icc" in os.path.basename(TAINT_DL):  # components and intent filters for the inter-component holes
        cp = ":".join(glob.glob(os.path.join(ROOT, "tools/flowdroid/lib/*.jar")))
        subprocess.run(["java", "-cp", cp, os.path.join(ROOT, "extract/Manifest.java"), apk, out],
                       capture_output=True, text=True, timeout=EXTRACT_TIMEOUT)
    return ok


def analyse(app, app_dir, deadline=None):
    fw, supers, (src, snk) = CTX
    prepare(app_dir, fw, supers, src, snk)
    with tempfile.TemporaryDirectory(prefix="souffle-", dir=SCRATCH) as out:
        why = run_souffle(app_dir, out, round(deadline - time.time()) if deadline else SOUFFLE_TIMEOUT)
        if why:
            process.reason = why
            return app, None
        save_graph(out, app, called_methods(app_dir), sink_call_count(app_dir))
        return app, dict((k, int(v)) for k, v in rows(out, "Stats"))


def process(item):
    """Worker: analyse one app. Apps without stored facts are extracted into a temporary
    directory that is deleted afterwards, so only the graph is kept. Returns (app, stats dict),
    (app, None) when the analysis ran out of memory / time, or (app, "error: ...") on a bug."""
    app, src_path = item
    t0 = time.time()
    budget = BUDGETS.get(app, TOTAL_TIMEOUT)
    deadline = t0 + budget if budget else None
    process.reason = "ok"
    try:
        res = _process(app, src_path, deadline)
    finally:
        if REASONS_FILE:
            with open(REASONS_FILE, "a") as f:
                f.write("%s\t%s\t%d\n" % (app, process.reason, round(time.time() - t0)))
    return res


def _process(app, src_path, deadline):
    with open(os.environ.get("ATTEMPTS_FILE") or os.path.join(ROOT, "data/android_attempts.txt"), "a") as f:
        f.write(app + "\n")  # lets a restarted run skip an app that keeps killing it
    try:
        if os.path.isdir(src_path):
            return analyse(app, src_path, deadline)
        with tempfile.TemporaryDirectory(prefix="facts-", dir=SCRATCH) as d:
            try:
                ok = extract(src_path, d, round(deadline - time.time()) if deadline else EXTRACT_TIMEOUT, app)
            except subprocess.TimeoutExpired:
                process.reason = "extract timeout"
                return app, None
            if not ok:
                process.reason = extract.reason
                return app, None
            return analyse(app, d, deadline)
    except subprocess.TimeoutExpired:
        process.reason = "timeout"
        return app, None
    except Exception as e:
        process.reason = "error: %r" % (e,)
        return app, "error: %r" % (e,)


def apps_to_build(app_glob):
    """(app, facts dir or APK path): stored facts where present, otherwise the APK."""
    items = {} if os.environ.get("FROM_APK") else {os.path.basename(d): d for d in glob.glob(os.path.join(ROOT, "facts_apk_all", app_glob))}
    for pick in glob.glob(os.path.join(ROOT, "bench/apks/pick*.txt")):
        for line in open(pick).read().split("\n"):
            if line.count("\t") == 1 and "\x00" not in line:  # skip lines damaged by an interrupted write
                pkg, apk = line.split("\t")
                path = os.path.join(ROOT, "bench/apks", apk)
                if pkg not in items and fnmatch.fnmatch(pkg, app_glob) and os.path.exists(path):
                    items[pkg] = path
    if os.environ.get("APK_LIST"):  # extra apps outside the F-Droid corpus: lines "name TAB apk path relative to the repository"
        for line in open(os.environ["APK_LIST"]).read().splitlines():
            if line.count("\t") == 1:
                pkg, apk = line.split("\t")
                if fnmatch.fnmatch(pkg, app_glob) and os.path.exists(os.path.join(ROOT, apk)):
                    items[pkg] = os.path.join(ROOT, apk)
    if APPS_FILE:
        keep = {l.split("\t")[0] for l in open(APPS_FILE).read().splitlines() if l.strip()}
        items = {k: v for k, v in items.items() if k in keep}
    return sorted(items.items())


def main():
    app_glob = sys.argv[1] if len(sys.argv) > 1 else "*"
    os.makedirs(GRAPHS, exist_ok=True)
    global CTX
    fw = {l.strip() for l in open(os.path.join(ROOT, "data/android_classes.txt"))}
    CTX = (fw, framework_supers(), sources_sinks())
    if SOUFFLE_BIN:  # a compiled program must come from the current TAINT_DL
        want = open(SOUFFLE_BIN + ".dl.md5").read().split()[0]
        have = hashlib.md5(open(TAINT_DL, "rb").read()).hexdigest()
        if want != have:
            sys.exit("SOUFFLE_BIN was compiled from another version of %s; recompile it" % TAINT_DL)
    failed_path = os.environ.get("FAILED_FILE") or os.path.join(ROOT, "data/android_failed.txt")
    failed = set(open(failed_path).read().split()) if os.path.exists(failed_path) else set()
    attempts_path = os.environ.get("ATTEMPTS_FILE") or os.path.join(ROOT, "data/android_attempts.txt")
    tries = {}
    if os.path.exists(attempts_path):
        for a in open(attempts_path, errors="replace").read().split():
            tries[a] = tries.get(a, 0) + 1
    todo = [(a, p) for a, p in apps_to_build(app_glob) if a not in failed and not graph_fresh(a)]
    apps = [(a, p) for a, p in todo if tries.get(a, 0) < MAX_ATTEMPTS]
    print("building %d apps (%d skipped after %d attempts)" % (len(apps), len(todo) - len(apps), MAX_ATTEMPTS), flush=True)
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor, as_completed
    # a worker killed from outside (e.g. by the kernel) raises BrokenProcessPool instead of hanging;
    # the run then exits non-zero and a supervisor can restart it
    with ProcessPoolExecutor(JOBS, mp_context=multiprocessing.get_context("fork")) as ex:
        for fut in as_completed([ex.submit(process, item) for item in apps]):
            app, stats = fut.result()
            if stats is None:
                with open(failed_path, "a") as ff:
                    ff.write(app + "\n")
                print(app, "souffle failed", flush=True)
            elif isinstance(stats, str):
                with open(os.path.join(ROOT, "data/android_errors.txt"), "a") as ff:
                    ff.write("%s\t%s\n" % (app, stats))
                print(app, stats, flush=True)
            else:
                print(app, stats, flush=True)


if __name__ == "__main__":
    main()
