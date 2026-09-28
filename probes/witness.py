"""Oracle 2 of the closing loop: witness tests that show a library flow exists by running it.

For each hole atom (method, src -> tgt), an LLM writes a small Java program that puts Probe.SRC
into the source endpoint, calls the real method (JDK or Robolectric's android-all), and reports
whether the target endpoint holds the marker. The label comes only from execution:
  flow        main run prints WITNESS, the control run (different source value) does not, and
              for a receiver or argument target, the target holds no marker when the call is skipped
  invalid     a control fails, or the marker reaches an input other than the source endpoint
  no-witness  the test ran but found no marker (inconclusive: tests cannot prove absence)
  error       did not compile or crashed after a repair attempt; skip = the model declined
Usage: witness.py MODEL TOP [CANDIDATES_JSONL]   (TOP data-carrying candidates, by rank)
Writes data/witness_results.jsonl (appends; atoms already tested are skipped).
"""
import hashlib, json, os, re, subprocess, sys, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WDIR = os.path.join(ROOT, "tools/witness")
CP = os.path.join(WDIR, "android-all-13-robolectric-9030017.jar") + ":" + os.path.join(WDIR, "classes")
JAVA = ["java", "--add-opens", "java.base/java.lang=ALL-UNNAMED", "--add-opens", "java.base/java.util=ALL-UNNAMED"]
URL = "https://openrouter.ai/api/v1/chat/completions"
KEY = os.environ["OPENROUTERS_MINE"]
SCRATCH = os.environ.get("SCRATCH_DIR", tempfile.gettempdir())

PROMPT = """Write Java 17 statements that build the inputs for one call of a library method.

Method: {cls}.{sub}  ({kind})
The test checks whether {src} carrying the value Probe.SRC makes {tgt} carry it after the call.
The harness declares these variables and then makes the call and the check itself:

{decls}
{call}
Probe.report({target});

Write ONLY the statements that assign {assign} (plain assignments, e.g. `a0 = "x";`), plus any
helper local variables you need. Rules:
- Put Probe.SRC into {srcvar}: a String gets Probe.SRC itself; other types get a value that contains
  it (an Intent with an extra, a List holding it, a byte[] of it, a Uri parsed from a string with it).
- Use Probe.SRC exactly once, in the statement that assigns {srcvar}. Never use Probe.MARKER.
- Build every other input without Probe.SRC. Do not call the method yourself.
- Classpath: the JDK and the real Android framework classes on a plain JVM: there is NO device,
  Context, Looper or Activity, so only use classes you can construct directly.
- If the inputs cannot be built on a plain JVM, reply with the single word SKIP.
Reply with only the statements."""


def jtype(t):
    return t.replace("$", ".")


def skeleton(c):
    """Declarations, call and target variable for atom c, written by the harness (not the model)."""
    sub = c["sub"]
    ret, rest = sub.split(" ", 1)
    name = rest[:rest.index("(")]
    ps = [p for p in rest[rest.index("(") + 1:-1].split(",") if p]
    cls = jtype(c["cls"])
    ctor = name == "<init>"
    static = c.get("kind") == "static"
    decls = ["%s a%d = %s;" % (jtype(t), i, default(t)) for i, t in enumerate(ps)]
    args = ", ".join("a%d" % i for i in range(len(ps)))
    if ctor:
        call = "%s recv = new %s(%s);" % (cls, cls, args)
    else:
        if not static:
            decls.insert(0, "%s recv = null;" % cls)
        target_call = "%s.%s(%s)" % (cls if static else "recv", name, args)
        call = ("%s ret = %s;" % (jtype(ret), target_call)) if ret != "void" else target_call + ";"
    def var(e):
        return {"this": "recv", "ret": "ret"}.get(e, "a" + e[3:])  # argN -> aN
    srcvar, tgtvar = var(c["src"]), var(c["tgt"])
    assign = [v for v in (["recv"] if (not ctor and not static) else []) + ["a%d" % i for i in range(len(ps))]]
    return decls, call, srcvar, tgtvar, assign


def sanitize(body, harness_vars):
    """Undo common deviations from the skeleton: redeclared harness variables become plain
    assignments, and the model's own Probe.report lines are dropped."""
    out = []
    for line in body.splitlines():
        if "Probe.report" in line:
            continue
        for v in harness_vars:
            line = re.sub(r"^(\s*)(?:final\s+)?[\w.<>\[\],? ]+\s+%s\s*=" % re.escape(v), r"\1%s =" % v, line)
        out.append(line)
    return "\n".join(out)


def marker_ok(body, srcvar, harness_vars):
    """Probe.SRC must reach only the source variable. Follow it through helper locals
    (`T x = ...Probe.SRC...;`) and reject any statement that puts a tainted value into another
    harness variable (the receiver or another argument), by assignment or by a call on it."""
    if "Probe.MARKER" in body or body.count("Probe.SRC") != 1:
        return False
    others = [v for v in harness_vars if v != srcvar]
    tainted = {"Probe.SRC"}
    for line in body.splitlines():
        head = line.strip()
        if not any(re.search(r"(?<![\w.])%s(?!\w)" % re.escape(t), head) for t in tainted):
            continue
        m = re.match(r"(?:[\w.<>\[\],? ]+\s+)?(\w+)\s*(?:=|\.|\[)", head)
        written = m.group(1) if m else ""
        if written in others:
            return False
        if written and written != srcvar:
            tainted.add(written)
    return True


def default(t):
    return {"boolean": "false", "char": "'x'", "long": "0L", "float": "0f", "double": "0d"}.get(
        t, "0" if t in ("int", "short", "byte") else "null")


def endpoint(name, params):
    if name == "this":
        return "the receiver object"
    if name == "ret":
        return "the return value"
    i = int(name[3:])
    return "argument %d (%s)" % (i, params[i] if i < len(params) else "?")


def llm(model, messages):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 1500, "messages": messages}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=120))
            return d["choices"][0]["message"]["content"], d["usage"].get("cost", 0)
        except Exception:
            time.sleep(2 ** attempt)
    return None, 0


def run_java(path, control):
    cmd = JAVA + (["-Dsrc.marker=CTRLVALUE91c2"] if control else []) + ["-cp", CP, path]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "timeout", ""
    lines = p.stdout.strip().splitlines()
    out = lines[-1] if lines else ""
    if p.returncode == 0 and out in ("WITNESS", "NO_WITNESS"):
        return out, ""
    return "error", (p.stderr or p.stdout)[-1500:]


def test_atom(model, c):
    sig = c["sub"]
    params = [p for p in sig[sig.index("(") + 1:-1].split(",") if p]
    kind = "constructor" if "<init>" in sig else ("static method" if c.get("kind") == "static" else "method")
    name = "W" + hashlib.md5(("%s|%s|%d" % (c["cls"], sig, c["k"])).encode()).hexdigest()[:10]
    decls, call, srcvar, tgtvar, assign = skeleton(c)
    prompt = PROMPT.format(cls=c["cls"], sub=sig, kind=kind, src=endpoint(c["src"], params),
                           tgt=endpoint(c["tgt"], params), decls="\n".join(decls), call=call, target=tgtvar,
                           assign=", ".join(assign), srcvar=srcvar)
    msgs = [{"role": "user", "content": prompt}]
    cost, res = 0, {"status": "error"}
    with tempfile.TemporaryDirectory(dir=SCRATCH, prefix="wit-") as d:
        for attempt in range(2):
            text, c1 = llm(model, msgs)
            cost += c1
            if text is None:
                break
            if text.strip().upper().startswith("SKIP"):
                res = {"status": "skip"}
                break
            m = re.search(r"```(?:java)?\s*(.*?)```", text, re.S)
            body = sanitize((m.group(1) if m else text).strip(), assign + [tgtvar])
            # the source value may reach only the source variable
            if not marker_ok(body, srcvar, assign + [tgtvar]):
                res = {"status": "invalid", "why": "marker placement", "code": body}
                msgs += [{"role": "assistant", "content": text},
                         {"role": "user", "content": "Use Probe.SRC exactly once, and let it reach only %s (no other input). Try again or reply SKIP." % srcvar}]
                continue
            code = "public class %s {\n  public static void main(String[] args) throws Throwable {\n    %s\n%s\n    %s\n    Probe.report(%s);\n  }\n}\n" % (
                name, "\n    ".join(decls), "\n".join("    " + l for l in body.splitlines()), call, tgtvar)
            path = os.path.join(d, name + ".java")
            open(path, "w").write(code)
            out, err = run_java(path, control=False)
            if out in ("error", "timeout"):
                res = {"status": "error", "err": err[-400:], "code": code}
                msgs += [{"role": "assistant", "content": text},
                         {"role": "user", "content": "It failed:\n" + err[-1200:] + "\nFix the statements (same rules), or reply SKIP."}]
                continue
            ctrl, _ = run_java(path, control=True)
            if out == "WITNESS" and tgtvar != "ret":
                # skip-call control: without the call, the target must not already hold the marker
                nocall = os.path.join(d, name + "N.java")
                skipped = code.replace("public class %s " % name, "public class %sN " % name).replace("    %s\n" % call, "")
                open(nocall, "w").write(skipped)
                skip, _ = run_java(nocall, control=False)
                if skip != "NO_WITNESS":
                    res = {"status": "invalid", "why": "target holds the marker without the call", "code": code}
                    break
            if out == "WITNESS":
                res = {"status": "flow" if ctrl == "NO_WITNESS" else "invalid", "control": ctrl, "code": code}
            else:
                res = {"status": "no-witness", "code": code}
            break
    return dict(c, witness=res["status"], detail={k: v for k, v in res.items() if k != "status"}, cost=cost)


def main():
    model, top = sys.argv[1], int(sys.argv[2])
    cand_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "data/leak_candidates.jsonl")
    sys.path.insert(0, os.path.join(ROOT, "analysis"))
    from closing import carries_data
    kinds = {(h["cls"], h["sig"]): h["kind"] for h in map(json.loads, open(os.path.join(ROOT, "data/holes_android_fw.jsonl")))}
    cands = [dict(c, kind=kinds.get((c["cls"], c["sub"]))) for c in map(json.loads, open(cand_path)) if carries_data(c)][:top]
    out = os.path.join(ROOT, "data/witness_results.jsonl")
    # atoms with a result count as done, except errors where no code came back (API failures)
    done = {(d["cls"], d["sub"], d["k"]) for d in map(json.loads, open(out))
            if d["witness"] != "error" or d["detail"].get("code")} if os.path.exists(out) else set()
    todo = [c for c in cands if (c["cls"], c["sub"], c["k"]) not in done]
    stats, cost = {}, 0
    with open(out, "a") as f, ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda c: test_atom(model, c), todo):
            f.write(json.dumps(r) + "\n")
            f.flush()
            stats[r["witness"]] = stats.get(r["witness"], 0) + 1
            cost += r["cost"]
    print("tested", len(todo), stats, "cost $%.3f" % cost)


if __name__ == "__main__":
    main()
