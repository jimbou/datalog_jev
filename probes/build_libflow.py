"""Build a labeled set of library-flow candidate atoms from FlowDroid manual summaries.

Each method gets the full candidate menu (arg_i/this -> ret/this/arg_j); an atom is
labeled true iff the summary has a flow between those bases (field paths collapsed).
Methods with callback gaps or implicit flows are skipped.
Output: data/libflow.jsonl, one method per line.
"""
import glob, json, os, subprocess, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMMUTABLE = {"java.lang.String", "java.lang.Integer", "java.lang.Long", "java.lang.Short",
             "java.lang.Byte", "java.lang.Boolean", "java.lang.Character", "java.lang.Double",
             "java.lang.Float", "java.lang.Class", "java.math.BigInteger", "java.math.BigDecimal"}
PRIMS = {"int", "long", "short", "byte", "boolean", "char", "double", "float"}


def base(ep, ret_type=None):
    """Collapse a summary endpoint to arg<i>, this or ret. A Field endpoint typed with the method's
    own return type (static factories such as Uri.parse) denotes the returned object."""
    t = ep.get("sourceSinkType")
    if t == "Field" and ret_type and ep.get("BaseType") == ret_type:
        return "ret"
    if t == "Parameter":
        return "arg%s" % ep.get("ParameterIndex")
    if t == "Field":
        return "this"
    if t == "Return":
        return "ret"
    return None


def returns_receiver(m):
    """True when the summary returns the whole receiver object by alias (builder-style methods)."""
    for fl in m.iter("flow"):
        fr, to = fl.find("from"), fl.find("to")
        if (fl.get("isAlias") == "true" and fr.get("sourceSinkType") == "Field" and fr.get("AccessPath") is None
                and to.get("sourceSinkType") == "Return" and to.get("AccessPath") is None):
            return True
    return False


def close_flows(m, flows):
    """Compose X -> this with a whole-receiver return: X -> ret."""
    if returns_receiver(m):
        flows |= {(s, "ret") for s, t in flows if t == "this" and s != "ret"}
    return flows


def parse():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/stubdroid/java.*.xml"))):
        cls = os.path.basename(f)[:-4].replace("%24", "$")
        for m in ET.parse(f).getroot().iter("method"):
            if any(e.get("sourceSinkType") in ("GapBaseObject", "Implicit") for e in m.iter()):
                continue
            flows = set()
            rt = m.get("id").split(" ")[0]
            for fl in m.iter("flow"):
                a, b = base(fl.find("from"), rt), base(fl.find("to"), rt)
                if a and b and a != b:
                    flows.add((a, b))
            rows.append({"cls": cls, "sig": m.get("id"), "flows": sorted(close_flows(m, flows))})
    return rows


def resolve(rows):
    inp = "".join("%s\t%s\n" % (r["cls"].replace("$", "$"), r["sig"]) for r in rows)
    out = subprocess.run(["java", os.path.join(ROOT, "probes/Sigs.java")], input=inp,
                         capture_output=True, text=True, check=True).stdout.splitlines()
    for r, line in zip(rows, out):
        found, kind, *_ = line.split("\t")
        r["found"], r["kind"] = found, kind


def menu(r):
    sig = r["sig"]
    ret = sig[:sig.index(" ")]
    ps = sig[sig.index("(") + 1:-1]
    params = ps.split(",") if ps else []
    kind = r["kind"]
    srcs = ["arg%d" % i for i in range(len(params))]
    if kind == "instance":
        srcs.append("this")
    tgts = []
    if ret != "void" and kind != "ctor":
        tgts.append("ret")
    if kind in ("instance", "ctor"):
        tgts.append("this")
    tgts += ["arg%d" % i for i, p in enumerate(params) if p not in PRIMS and p not in IMMUTABLE]
    return [(s, t) for s in srcs for t in tgts if s != t]


def main():
    rows = parse()
    resolve(rows)
    kept, stats = [], {"methods": 0, "atoms": 0, "true": 0, "unlisted_flow": 0}
    for r in rows:
        if r["found"] != "found":
            continue
        atoms = menu(r)
        if not atoms:
            continue
        fl = set(map(tuple, r["flows"]))
        stats["unlisted_flow"] += len(fl - set(atoms))
        r["atoms"] = [{"src": s, "tgt": t, "label": (s, t) in fl} for s, t in atoms]
        stats["methods"] += 1
        stats["atoms"] += len(atoms)
        stats["true"] += sum(a["label"] for a in r["atoms"])
        kept.append(r)
    with open(os.path.join(ROOT, "data/libflow.jsonl"), "w") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")
    print("parsed", len(rows), "missing/noclass", sum(r["found"] != "found" for r in rows), stats,
          file=sys.stderr)


if __name__ == "__main__":
    main()
