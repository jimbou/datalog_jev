"""Price callback holes (objects exposed to JavaScript, F4a) with a language model.

Usage: price_cb.py MODEL GRAPHS_DIR OUT.jsonl      (env BACKEND=claude|codex, default claude; PRICE_THREADS, default 6)
For every relevant candidate (registration site -> method) stored in the graphs (cb_sub / cb_info, written by taint_cb.dl),
asks the model once per registration site for the probability that JavaScript in the WebView can call each candidate method
of the registered object and read its return value. The model sees what a reader of the code would see: the registering
method, each candidate method's signature, its annotations, whether it is public, and the app's target SDK. It never sees
the answer key. Rows already in OUT are skipped, so the script can be restarted. Rows: {app, sub, p}.
"""
import collections, glob, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cli_llm

SYSTEM = ("You are an expert on Android WebView security. An app registers a Java object with "
          "WebView.addJavascriptInterface(object, name). For each candidate method of the registered object, estimate the "
          "probability that JavaScript running in the WebView can call that method and read its return value in ordinary "
          "executions on the devices the app targets. Give calibrated probabilities between 0 and 1 (small values such as "
          "0.02 when you are sure it cannot). Answer only with a JSON object mapping each candidate number to a probability.")


def questions(gdir):
    out = []
    for g in sorted(glob.glob(os.path.join(gdir, "*.npz"))):
        z = np.load(g)
        if "cb_info" not in z.files:
            continue
        app = os.path.basename(g)[:-4]
        info = collections.defaultdict(lambda: collections.defaultdict(list))
        for sub, what, val in json.loads(str(z["cb_info"])):
            info[sub][what].append(val)
        by_site = collections.defaultdict(list)
        for sub in z["cb_sub"].tolist():
            site, meth = sub.split(" -> ", 1)
            by_site[site].append((sub, meth))
        for site, cands in by_site.items():
            out.append({"app": app, "site": site, "sdk": sorted(set(info[cands[0][0]]["target_sdk"])),
                        "cands": [(sub, meth, info[sub]) for sub, meth in cands]})
    return out


def ask(model, q):
    m = re.match(r"<([^:]+): ([^>]+)>/(\d+)", q["site"])
    lines = ["App package: %s" % q["app"], "Target SDK version: %s" % (", ".join(q["sdk"]) or "unknown"),
             "Registering method: %s.%s (statement %s)" % (m.group(1), m.group(2), m.group(3)) if m else q["site"],
             "", "Candidate methods of the registered object:"]
    for k, (sub, meth, inf) in enumerate(q["cands"]):
        lines.append("%d: %s (public=%s, annotations: %s)" % (
            k, meth, "true" if inf["public"] else "false", ", ".join(sorted(set(inf["annotation"]))) or "none"))
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
    print("registration sites to ask:", len(qs), "candidates:", sum(len(q["cands"]) for q in qs), file=sys.stderr, flush=True)
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
