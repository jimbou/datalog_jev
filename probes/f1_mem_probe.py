"""F1 diagnostic: peak memory (max RSS) and time of the Soufflé interpreter and the compiled programs on one app, without
the address-space limit, to see whether the compiled program fails on real memory or only on reserved address space.

Usage: python3 probes/f1_mem_probe.py APK OUT.tsv   (env as for run_android.py; runs each variant once, 4 threads)
"""
import os, resource, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis"))
import run_android as ra

apk, out_path = sys.argv[1], sys.argv[2]
fw = {l.strip() for l in open(os.path.join(ra.ROOT, "data/android_classes.txt"))}
fw_ctx = (fw, ra.framework_supers(), *ra.sources_sinks())
variants = [("interp", [ra.SOUFFLE, "-j", "4"], [ra.TAINT_DL]),
            ("bin1", [os.path.join(ra.ROOT, "tools/taint_bin/taint"), "-j", "4"], []),
            ("par", [os.path.join(ra.ROOT, "tools/taint_bin_par/taint"), "-j", "4"], [])]
with tempfile.TemporaryDirectory(prefix="facts-", dir=ra.SCRATCH) as d:
    t0 = time.time()
    assert ra.extract(apk, d, 2100), "extraction failed"
    ra.prepare(d, *fw_ctx)
    with open(out_path, "a") as f:
        f.write("extract\t-\t%d\n" % (time.time() - t0))
    for name, cmd, tail in variants:
        with tempfile.TemporaryDirectory(prefix="souffle-", dir=ra.SCRATCH) as o:
            t0 = time.time()
            p = subprocess.run(["/usr/bin/time", "-f", "%M", *cmd, "-F", d, "-D", o, *tail], capture_output=True, text=True, timeout=2100)
            rss_kb = int(p.stderr.strip().splitlines()[-1]) if p.stderr.strip() else -1
            with open(out_path, "a") as f:
                f.write("%s\trc=%d\t%d s\tmax RSS %.1f GB\n" % (name, p.returncode, time.time() - t0, rss_kb / 2**20))
