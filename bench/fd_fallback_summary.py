"""Summary of bench/fd_fallback.py (run on the server: reads data/fd_fallback.jsonl, data/fd_fallback_runs/*.log, data/graphs_f1*)."""
import json, os, collections
os.chdir(os.path.expanduser("~/receipts/data"))
rows = [json.loads(l) for l in open("fd_fallback.jsonl")]
fb = [d for d in rows if d["kind"] == "fallback"]; ct = [d for d in rows if d["kind"] == "control"]
def nosrc(app):
    p = "fd_fallback_runs/%s.log" % app
    return os.path.exists(p) and "No sources found" in open(p, errors="replace").read()
ok = [d for d in fb if d["fdx"]["state"] == "Success"]
print("FALLBACK: %d runs, success %d (no sources found: %d, with sinks: %d)" % (len(fb), len(ok), sum(nosrc(d["app"]) for d in ok), sum(1 for d in ok if d["fdx"]["sinks"])))
print("  states", dict(collections.Counter(d["fdx"]["state"] for d in fb)))
print("  successes:", [(d["app"], d["fdx"]["seconds"], len(d["fdx"]["sinks"] or []), "nosrc" if nosrc(d["app"]) else "") for d in ok])
ours = set(os.path.basename(f)[:-4] for f in os.listdir("graphs_f1e_fb")) | set(os.path.basename(f)[:-4] for f in os.listdir("graphs_f1"))
print("  FD fallback successes also rescued by us:", sum(d["app"] in ours for d in ok))
cok = [d for d in ct if d["fdx"]["state"] == "Success" and d.get("base_sinks") is not None]
lost = kept = new = apps_lost = 0
for d in cok:
    b, x = set(d["base_sinks"]), set(d["fdx"]["sinks"] or [])
    lost += len(b - x); kept += len(b & x); new += len(x - b); apps_lost += bool(b - x)
print("CONTROL: %d runs, success %d (compared %d); leaks (distinct sink statements) in full run %d: kept %d, lost %d (%.1f%%), new %d; apps losing a leak %d of %d" % (
    len(ct), sum(d["fdx"]["state"] == "Success" for d in ct), len(cok), lost + kept, kept, lost, 100 * lost / max(1, lost + kept), new, apps_lost, len(cok)))
print("  control states", dict(collections.Counter(d["fdx"]["state"] for d in ct)))
print("  no sources found among control successes:", sum(nosrc(d["app"]) for d in cok))
