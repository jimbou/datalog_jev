"""Stated-confidence pricer: Sonnet 5 gives a probability for every candidate flow of a method (baseline B5).

Usage: run_sonnet_price.py MODEL TAG DATASET [LIMIT]   (env NO_REASONING=1 turns hidden reasoning off for models that have it; PRICE_THREADS sets the number of parallel requests;
  BACKEND=claude or codex asks through a logged-in Claude Code / Codex CLI instead of OpenRouter, see cli_llm.py;
  PRICE_PROMPT=definition asks under the written flow definition of the paper's Appendix A (the rubric of the labels);
  SAMPLES=k asks k times per method and prices each flow at the highest answer, keeping every sample in "samples")
  DATASET data/<DATASET>.jsonl hole records (cls, sig, kind, atoms)
Writes data/jev_<DATASET>_<TAG>_r0.jsonl rows {cls, sig, p: [prob, ...], cost}; priced methods are skipped, so it
can be restarted. evaluate.py reads it like a Jev price file (pricing name TAG). The question and the flow rule
are the same as the silver labels' (run_oracle.py); only the answer is a probability instead of yes / no.
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from run_jev import ROOT, endpoint, state
import cli_llm

URL = "https://openrouter.ai/api/v1/chat/completions"
KEY = os.environ.get("OPENROUTERS_MINE", "")
BACKEND = os.environ.get("BACKEND", "openrouter")
SYSTEM = ("You are an expert on the Java and Android framework APIs and on static taint analysis. "
          "For a library method, estimate for each candidate flow the probability that taint propagates under the "
          "usual taint-wrapper semantics: if the source holds sensitive data before the call, the target may hold "
          "that data, or data derived from it (including through fields or container contents), after the call. "
          "Give calibrated probabilities between 0 and 1 (use small values such as 0.02 for flows you are sure do not "
          "exist). Answer only with a JSON object mapping each question id to a number.")


DEFINITION = ("You are an expert on the Java and Android framework APIs. For a library method, estimate for each candidate "
              "flow the probability that data flows from X to Y under this definition. Method M is called with X holding a "
              "secret; after the call, is a piece of the secret in Y, in ordinary executions with standard arguments? It is a "
              "flow when X's data is copied or computed into Y, when X is stored in Y as the method's purpose (including "
              "keeping a reference to X), or when Y is read out of X (including its size, emptiness or metadata). It is not a "
              "flow when X only picks which existing thing is used or returned (an index, a lookup key), only controls how "
              "much, when or whether (a flag, a timeout, a boolean test result), only changes incidental state (caches, "
              "listeners' bookkeeping, back-pointers), would matter only through a custom override, callback, other OS "
              "version or unusual argument, or has no connection. Give calibrated probabilities between 0 and 1 (use small "
              "values such as 0.02 for flows you are sure do not exist). Answer only with a JSON object mapping each "
              "question id to a number.")
if os.environ.get("PRICE_PROMPT") == "definition":
    SYSTEM = DEFINITION
SAMPLES = int(os.environ.get("SAMPLES", "1"))


def ask(model, r):
    """SAMPLES > 1: the method is asked SAMPLES times; each flow is priced at the highest answer."""
    if SAMPLES > 1:
        runs = [ask_once(model, r) for _ in range(SAMPLES)]
        bad = [x for x in runs if "error" in x]
        if bad:
            return {"cls": r["cls"], "sig": r["sig"], "error": bad[0]["error"]}
        return {"cls": r["cls"], "sig": r["sig"], "p": [max(ps) for ps in zip(*(x["p"] for x in runs))],
                "samples": [x["p"] for x in runs], "cost": sum(x["cost"] for x in runs)}
    return ask_once(model, r)


def ask_once(model, r):
    """A method with more than 20 candidate flows is asked in chunks of 15 (one long answer can be cut off)."""
    if len(r["atoms"]) > 20:
        ps, cost = [], 0.0
        for i in range(0, len(r["atoms"]), 15):
            sub = dict(r, atoms=r["atoms"][i:i + 15])
            res = ask1(model, sub)
            if "error" in res:
                return {"cls": r["cls"], "sig": r["sig"], "error": res["error"]}
            ps += res["p"]
            cost += res["cost"]
        return {"cls": r["cls"], "sig": r["sig"], "p": ps, "cost": cost}
    return ask1(model, r)


def ask1(model, r):
    st, params = state(r)
    qs = "\n".join("%d: %s -> %s" % (k, endpoint(a["src"], params), endpoint(a["tgt"], params))
                   for k, a in enumerate(r["atoms"]))
    extra = {"reasoning": {"enabled": False}} if os.environ.get("NO_REASONING") else {}
    body = json.dumps({**extra, "model": model, "temperature": 0, "max_tokens": 400 + 25 * len(r["atoms"]),
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": st + "\n\nCandidate flows:\n" + qs}]}).encode()
    for attempt in range(5):
        try:
            if BACKEND != "openrouter":
                text = cli_llm.chat(BACKEND, model, SYSTEM, st + "\n\nCandidate flows:\n" + qs)
                d = {"choices": [{"message": {"content": text}}], "usage": {"cost": cli_llm.last_cost()}}  # API-equivalent
            else:
                req = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
                d = json.load(urllib.request.urlopen(req, timeout=120))
            obj = json.loads(re.search(r"\{.*\}", d["choices"][0]["message"]["content"], re.S).group(0))
            p = [min(0.99, max(0.01, float(obj.get(str(k), obj.get(k, 0.5))))) for k in range(len(r["atoms"]))]
            return {"cls": r["cls"], "sig": r["sig"], "p": p, "cost": d["usage"].get("cost", 0)}
        except Exception as e:
            err = e
            time.sleep(2 ** attempt)
    return {"cls": r["cls"], "sig": r["sig"], "error": repr(err)}


def main():
    model, tag, dataset = sys.argv[1:4]
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
    rows = [r for r in map(json.loads, open(os.path.join(ROOT, "data/%s.jsonl" % dataset))) if r["atoms"]][:limit]
    out = os.path.join(ROOT, "data/jev_%s_%s_r0.jsonl" % (dataset, tag))
    done = {(d["cls"], d["sig"]) for d in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [r for r in rows if (r["cls"], r["sig"]) not in done]
    errs = cost = 0
    with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("PRICE_THREADS", "12"))) as ex:
        for res in ex.map(lambda r: ask(model, r), todo):
            if "error" in res:
                errs += 1
            else:
                cost += res["cost"]
                f.write(json.dumps(res) + "\n")
                f.flush()
    print(tag, "priced", len(todo) - errs, "errors", errs, "cost $%.3f" % cost, file=sys.stderr)


if __name__ == "__main__":
    main()
