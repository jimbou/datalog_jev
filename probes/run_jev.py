"""Price every library-flow atom with Jev (one call per method, all atoms as Noul questions).

Usage: run_jev.py WORDING REPEAT [LIMIT] [DATASET]
Reads data/<DATASET>.jsonl (default libflow) and appends to data/jev_<WORDING>_r<REPEAT>.jsonl
(data/jev_<DATASET>_<WORDING>_r<REPEAT>.jsonl for other datasets); priced methods are skipped.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://openrouter.ai/api/alpha/decisions"
KEY = os.environ.get("OPENROUTERS_MINE", "")

WORDINGS = {
    "taint": "Taint-tracking semantics: if {src} holds sensitive (tainted) data before the call, "
             "then after the call {tgt} holds that data or data derived from it.",
    "may": "During this call, data from {src} can flow into {tgt}.",
    "choice": "Taint-tracking semantics: if {src} holds sensitive (tainted) data before the call, "
              "does {tgt} hold that data or data derived from it after the call?",
}
WORDINGS["choice-obj"] = ("Taint is tracked at object granularity: a tainted object taints everything read or "
                          "obtained from it (its fields, getter results, contents, and derived values). "
                          "If {src} is tainted before the call, is {tgt} tainted after the call?")
CHOICE = {"yes": "yes, the tainted data reaches it", "no": "no, the tainted data does not reach it"}


def endpoint(name, params):
    if name == "this":
        return "the receiver object (this)"
    if name == "ret":
        return "the return value"
    i = int(name[3:])
    return "argument %d (%s)" % (i, params[i])


def state(r):
    sig = r["sig"]
    ps = sig[sig.index("(") + 1:-1]
    kind = {"ctor": "constructor", "instance": "instance method", "static": "static method"}[r["kind"]]
    return ("Java library method, source code not available.\nClass: %s\nSignature: %s\nKind: %s"
            % (r["cls"], sig, kind)), (ps.split(",") if ps else [])


def price(a):
    return a["probabilities"]["yes"] if a["type"] == "choice" else a["noul"]


def ask(r, wording):
    st, params = state(r)
    qs = {}
    for k, a in enumerate(r["atoms"]):
        text = WORDINGS[wording].format(src=endpoint(a["src"], params), tgt=endpoint(a["tgt"], params))
        if wording.startswith("choice"):
            qs["a%d" % k] = {"type": "choice", "instructions": text, "criteria": CHOICE}
        else:
            qs["a%d" % k] = {"type": "noul", "instructions": text}
    body = json.dumps({"model": "~typesafe/jev-latest", "state": st, "questions": qs}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY,
                                                     "Content-Type": "application/json"})
            resp = json.load(urllib.request.urlopen(req, timeout=60))
            ans = resp["answers"]
            return {"cls": r["cls"], "sig": r["sig"], "model": resp["model"],
                    "cost": resp["usage"].get("cost"),
                    "p": [price(ans["a%d" % k]) for k in range(len(r["atoms"]))]}
        except Exception as e:
            err = e
            time.sleep(2 ** attempt)
    return {"cls": r["cls"], "sig": r["sig"], "error": repr(err)}


def main():
    wording, rep = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "all" else None
    dataset = sys.argv[4] if len(sys.argv) > 4 else "libflow"
    rows = [r for r in map(json.loads, open(os.path.join(ROOT, "data/%s.jsonl" % dataset))) if r["atoms"]][:limit]
    tag = wording if dataset == "libflow" else "%s_%s" % (dataset, wording)
    out = os.path.join(ROOT, "data/jev_%s_r%s.jsonl" % (tag, rep))
    done = set()
    if os.path.exists(out):
        done = {(d["cls"], d["sig"]) for d in map(json.loads, open(out)) if "p" in d}
    todo = [r for r in rows if (r["cls"], r["sig"]) not in done]
    errs = 0
    with open(out, "a") as f, ThreadPoolExecutor(16) as ex:
        for res in ex.map(lambda r: ask(r, wording), todo):
            errs += "error" in res
            if "p" in res:
                f.write(json.dumps(res) + "\n")
    print(wording, rep, "priced", len(todo) - errs, "errors", errs, file=sys.stderr)


if __name__ == "__main__":
    main()
