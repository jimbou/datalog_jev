"""Price inter-component (Intent) holes with a language model (experiment 4).

Usage: price_icc.py MODEL GRAPHS_DIR OUT.jsonl      (env BACKEND=claude|codex, default claude; PRICE_THREADS, default 6)
For every relevant candidate (send site -> component) stored in the graphs (icc_sub / icc_info, written by taint_icc.dl), asks
the model once per send site for the probability that the Intent sent there is delivered to each candidate component. The
model sees what a reader of the code would see: the sending method, the Intent's constant target classes and actions (if
any), and each component's kind, exported flag and intent-filter actions. It never sees the answer key. Rows already in
OUT are skipped, so the script can be restarted. Rows: {app, sub, p}.
"""
import collections, glob, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cli_llm

SYSTEM = ("You are an expert on Android inter-component communication. An app sends an Intent from a call site. For each "
          "candidate component of the same app, estimate the probability that this Intent can be delivered to that component "
          "in ordinary executions (explicit target class, or an implicit Intent whose action matches the component's intent "
          "filter). Give calibrated probabilities between 0 and 1 (small values such as 0.02 when you are sure it cannot). "
          "Answer only with a JSON object mapping each candidate number to a probability.")


def questions(gdir):
    out = []
    for g in sorted(glob.glob(os.path.join(gdir, "*.npz"))):
        z = np.load(g)
        if "icc_info" not in z.files:
            continue
        app = os.path.basename(g)[:-4]
        info = collections.defaultdict(lambda: collections.defaultdict(list))
        for sub, what, val in json.loads(str(z["icc_info"])):
            info[sub][what].append(val)
        by_site = collections.defaultdict(list)
        for sub in z["icc_sub"].tolist():
            site, comp = sub.rsplit(" -> ", 1)
            by_site[site].append((sub, comp))
        for site, cands in by_site.items():
            first = info[cands[0][0]]
            out.append({"app": app, "site": site, "targets": sorted(set(first["target"])), "actions": sorted(set(first["action"])),
                        "cands": [(sub, comp, info[sub]) for sub, comp in cands]})
    return out


def ask(model, q):
    m = re.match(r"<([^:]+): ([^>]+)>/(\d+)", q["site"])
    lines = ["App package: %s" % q["app"], "Sending method: %s.%s (statement %s)" % (m.group(1), m.group(2), m.group(3)) if m else q["site"],
             "Intent explicit target class(es) known from constants: %s" % (", ".join(q["targets"]) or "none found"),
             "Intent action(s) known from constants: %s" % (", ".join(q["actions"]) or "none found"), "", "Candidate components:"]
    for k, (sub, comp, inf) in enumerate(q["cands"]):
        lines.append("%d: %s (%s, exported=%s, filter actions: %s)" % (
            k, comp, ",".join(inf["kind"]) or "?", ",".join(inf["exported"]) or "?", ", ".join(sorted(set(inf["filter"]))) or "none"))
    backend = os.environ.get("BACKEND", "claude")
    for attempt in range(4):
        try:
            text = cli_llm.chat(backend, model, SYSTEM, "\n".join(lines))
            obj = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            return [{"app": q["app"], "sub": sub, "p": min(0.99, max(0.01, float(obj.get(str(k), obj.get(k, 0.5)))))}
                    for k, (sub, _, _) in enumerate(q["cands"])]
        except Exception as e:
            err = e
            time.sleep(2 ** attempt)
    return {"error": repr(err), "app": q["app"], "site": q["site"]}


def main():
    model, gdir, out = sys.argv[1:4]
    done = {(d["app"], d["sub"]) for d in map(json.loads, open(out))} if os.path.exists(out) else set()
    qs = [q for q in questions(gdir) if any((q["app"], sub) not in done for sub, _, _ in q["cands"])]
    print("send sites to ask:", len(qs), "candidates:", sum(len(q["cands"]) for q in qs), file=sys.stderr, flush=True)
    errs = 0
    with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("PRICE_THREADS", "6"))) as ex:
        for res in ex.map(lambda q: ask(model, q), qs):
            if isinstance(res, dict):
                errs += 1
                continue
            for r in res:
                f.write(json.dumps(r) + "\n")
            f.flush()
    print("priced sites", len(qs) - errs, "errors", errs, file=sys.stderr)


if __name__ == "__main__":
    main()
