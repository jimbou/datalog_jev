"""Baseline scorer: a general LLM's P(yes) from token logprobs, one question per atom.

Usage: run_llm.py MODEL TAG [DATASET]
Writes data/llm-<TAG>_r0.jsonl in the same per-method format as run_jev.py.
"""
import json, math, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from run_jev import ROOT, WORDINGS, endpoint, state

URL = "https://openrouter.ai/api/v1/chat/completions"
KEY = os.environ["OPENROUTERS_MINE"]


def p_yes(model, st, q):
    body = json.dumps({"model": model, "max_tokens": 1, "temperature": 0, "logprobs": True, "top_logprobs": 10,
                       "provider": {"require_parameters": True},
                       "messages": [{"role": "system", "content": "Answer with exactly one word: yes or no."},
                                    {"role": "user", "content": st + "\n\n" + q}]}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=60))
            top = d["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
            yes = sum(math.exp(t["logprob"]) for t in top if t["token"].strip().lower() == "yes")
            no = sum(math.exp(t["logprob"]) for t in top if t["token"].strip().lower() == "no")
            return yes / (yes + no) if yes + no > 0 else 0.5, d["usage"].get("cost", 0)
        except Exception:
            time.sleep(2 ** attempt)
    return None, 0


def price(model, r):
    st, params = state(r)
    ps, cost = [], 0
    for a in r["atoms"]:
        q = WORDINGS["choice"].format(src=endpoint(a["src"], params), tgt=endpoint(a["tgt"], params))
        p, c = p_yes(model, st, q)
        if p is None:
            return {"cls": r["cls"], "sig": r["sig"], "error": True}
        ps.append(p)
        cost += c
    return {"cls": r["cls"], "sig": r["sig"], "model": model, "cost": cost, "p": ps}


def main():
    model, tag = sys.argv[1], sys.argv[2]
    dataset = sys.argv[3] if len(sys.argv) > 3 else "libflow"
    rows = [r for r in map(json.loads, open(os.path.join(ROOT, "data/%s.jsonl" % dataset))) if r["atoms"]]
    out = os.path.join(ROOT, "data/llm-%s_r0.jsonl" % tag)
    done = {(d["cls"], d["sig"]) for d in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [r for r in rows if (r["cls"], r["sig"]) not in done]
    errs = 0
    with open(out, "a") as f, ThreadPoolExecutor(16) as ex:
        for res in ex.map(lambda r: price(model, r), todo):
            if "error" in res:
                errs += 1
            else:
                f.write(json.dumps(res) + "\n")
    print(tag, "priced", len(todo) - errs, "errors", errs, file=sys.stderr)


if __name__ == "__main__":
    main()
