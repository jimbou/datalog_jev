"""Silver labels for hole atoms from a strong LLM (one JSON answer per method).

Usage: run_oracle.py MODEL TAG DATASET [KEYS_FILE]
  DATASET   data/<DATASET>.jsonl hole records (cls, sig, kind, atoms)
  KEYS_FILE optional file of "cls<TAB>sig" lines restricting which methods to label
Writes data/oracle-<TAG>.jsonl: {cls, sig, labels: [bool...], cost}
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from run_jev import ROOT, endpoint, state

URL = "https://openrouter.ai/api/v1/chat/completions"
KEY = os.environ["OPENROUTERS_MINE"]
SYSTEM = ("You are an expert on the Java and Android framework APIs and on static taint analysis. "
          "For a library method, decide for each candidate flow whether taint propagates under the usual "
          "taint-wrapper semantics: if the source holds sensitive data before the call, the target may hold "
          "that data, or data derived from it (including through fields or container contents), after the call. "
          "Answer only with a JSON object mapping each question id to true or false.")


def ask(model, r):
    st, params = state(r)
    qs = "\n".join("%d: %s -> %s" % (k, endpoint(a["src"], params), endpoint(a["tgt"], params))
                   for k, a in enumerate(r["atoms"]))
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 400,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": st + "\n\nCandidate flows:\n" + qs}]}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=120))
            text = d["choices"][0]["message"]["content"]
            obj = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            labels = [bool(obj.get(str(k), obj.get(k, False))) for k in range(len(r["atoms"]))]
            return {"cls": r["cls"], "sig": r["sig"], "labels": labels, "cost": d["usage"].get("cost", 0)}
        except Exception as e:
            err = e
            time.sleep(2 ** attempt)
    return {"cls": r["cls"], "sig": r["sig"], "error": repr(err)}


def main():
    model, tag, dataset = sys.argv[1:4]
    rows = [r for r in map(json.loads, open(os.path.join(ROOT, "data/%s.jsonl" % dataset))) if r["atoms"]]
    if len(sys.argv) > 4:
        keys = {tuple(l.rstrip("\n").split("\t")) for l in open(sys.argv[4])}
        rows = [r for r in rows if (r["cls"], r["sig"]) in keys]
    out = os.path.join(ROOT, "data/oracle-%s.jsonl" % tag)
    done = {(d["cls"], d["sig"]) for d in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [r for r in rows if (r["cls"], r["sig"]) not in done]
    errs = cost = 0
    with open(out, "a") as f, ThreadPoolExecutor(12) as ex:
        for res in ex.map(lambda r: ask(model, r), todo):
            if "error" in res:
                errs += 1
            else:
                cost += res["cost"]
                f.write(json.dumps(res) + "\n")
    print(tag, "labeled", len(todo) - errs, "errors", errs, "cost $%.3f" % cost, file=sys.stderr)


if __name__ == "__main__":
    main()
