"""Generate the paper's pgfplots figures and data tables from the stored statistics.

Usage (from the repository root): python3 paper/make_figs.py
Inputs: data/paper_stats.json (analysis/paper_stats.py), data/k1c_summary_final_a05.log (analysis/k1_summary.py --class-level).
Outputs: paper/figs/*.tex, included by the section files.
"""
import json, math, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "paper/figs")
S = json.load(open(os.path.join(ROOT, "data/paper_stats.json")))
NAMES = {"choice-obj": "Jev", "sonnetp": "Sonnet~5", "b6": "Classifier", "b6c": "Classifier",
         "freq": "Frequency prior", "uniform": "Counting", "b3": "LLM as fact", "b6jc": "Classifier + Jev price"}
STYLE = {"choice-obj": "blue, thick", "sonnetp": "red, thick, dashed", "b6": "teal, thick, dotted", "b6c": "teal, thick, dotted",
         "freq": "orange, thick, dashdotted", "uniform": "gray, thick", "b3": "violet, thick, densely dashed",
         "b6jc": "brown, thick, loosely dashed"}
EPS = 0.1


def base(p):
    return p.split("-", 1)[1] if p.startswith(("k2-", "ah2-", "au-")) else p


def thin(curve, xmax=1.0):
    """Keep the points that change the curve, at most about 120."""
    pts, last = [], None
    for t, x, y in curve:
        if x > xmax:
            break
        if last is None or abs(x - last[0]) > 0.004 or abs(y - last[1]) > 0.004:
            pts.append((x, y))
            last = (x, y)
    return pts


def risk_coverage(pricings, name, caption_note):
    lines = [r"\begin{tikzpicture}",
             r"\begin{axis}[width=0.98\linewidth, height=5.4cm, xmin=0, xmax=1, ymin=0, ymax=0.5,",
             r"  xlabel={Share of leak-free hard-slice sinks cleared}, ylabel={Apps with a wrong clearance},",
             r"  legend style={font=\scriptsize, at={(0.02,0.98)}, anchor=north west}, legend cell align=left,",
             r"  tick label style={font=\scriptsize}, label style={font=\small}, grid=major, grid style={gray!20}]"]
    for p in pricings:
        if p not in S:
            continue
        if base(p) == "b3":  # yes/no taken as fact: one operating point (every receipt fact answered "no"; bound <= 0.5)
            t, x, y = max((c for c in S[p]["curve"] if c[0] <= 0.5), key=lambda c: c[0])
            lines.append(r"\addplot[only marks, mark=diamond*, mark size=3pt, violet] coordinates {(%.4f,%.4f)};" % (x, y))
            lines.append(r"\addlegendentry{%s}" % NAMES[base(p)])
            continue
        pts = thin(S[p]["curve"])
        lines.append(r"\addplot[%s, const plot mark left] coordinates {%s};" % (STYLE[base(p)], " ".join("(%.4f,%.4f)" % q for q in pts)))
        lines.append(r"\addlegendentry{%s}" % NAMES[base(p)])
    for p in pricings:  # certified operating points at alpha 0.05 (mean over half splits)
        if p not in S or base(p) == "b3":
            continue
        c = S[p]["certified"]["0.05"]
        if c["wrong_mean"] is not None and c["cleared_mean"] > 0:
            lines.append(r"\addplot[only marks, mark=*, mark size=1.8pt, %s, forget plot] coordinates {(%.4f,%.4f)};"
                         % (STYLE[base(p)].split(",")[0], c["cleared_mean"], c["wrong_mean"]))
    lines.append(r"\addplot[black, densely dotted, forget plot] coordinates {(0,0.05) (1,0.05)};")
    lines.append(r"\node[font=\scriptsize, anchor=south east] at (axis cs:1,0.05) {$\alpha=0.05$};")
    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    open(os.path.join(OUT, name), "w").write("\n".join(lines) + "\n")


def learning():
    p = "choice-obj"
    L = S[p]["learning"]
    lines = [r"\begin{tikzpicture}",
             r"\begin{axis}[width=0.98\linewidth, height=4.8cm, xmin=0, xmax=290, ymin=0, ymax=0.5,",
             r"  xlabel={Calibration apps $n$}, ylabel={Share cleared (held out)},",
             r"  legend style={font=\scriptsize, at={(0.98,0.04)}, anchor=south east}, legend cell align=left,",
             r"  tick label style={font=\scriptsize}, label style={font=\small}, grid=major, grid style={gray!20}]"]
    for alpha, st in ((0.1, "blue, thick, mark=*"), (0.05, "red, thick, mark=square*"), (0.02, "teal, thick, mark=triangle*")):
        pts = [(l["n"], l["cleared"]) for l in L if l["alpha"] == alpha]
        lines.append(r"\addplot[%s, mark size=1.5pt] coordinates {%s};" % (st, " ".join("(%d,%.4f)" % q for q in pts)))
        lines.append(r"\addlegendentry{$\alpha=%g$}" % alpha)
        nstar = math.ceil(math.log(EPS) / math.log(1 - alpha))
        lines.append(r"\addplot[%s, densely dotted, thin, forget plot] coordinates {(%d,0) (%d,0.5)};" % (st.split(",")[0], nstar, nstar))
    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    open(os.path.join(OUT, "learning.tex"), "w").write("\n".join(lines) + "\n")


def deletion():
    rows = {}
    for l in open(os.path.join(ROOT, "data/k1c_summary_final_a05.log")):
        m = re.match(r"\| (\d+)% \| (\S+) \| (\d+) \|.*\| ([\d.]+)% \|\s*$", l)
        if m:
            rows.setdefault(m.group(2), []).append((int(m.group(1)), float(m.group(4)) / 100))
    lines = [r"\begin{tikzpicture}",
             r"\begin{axis}[width=0.98\linewidth, height=5cm, xmin=5, xmax=95, ymin=0, ymax=1,",
             r"  xlabel={Classes deleted (\%)}, ylabel={Share cleared at $\alpha=0.05$}, xtick={10,25,50,75,90},",
             r"  legend style={font=\scriptsize, at={(0.5,-0.32)}, anchor=north}, legend cell align=left, legend columns=3,",
             r"  tick label style={font=\scriptsize}, label style={font=\small}, grid=major, grid style={gray!20}]"]
    for p in ("choice-obj", "sonnetp", "b6c", "b6jc", "b3", "uniform"):
        if p in rows:
            lines.append(r"\addplot[%s, mark=*, mark size=1.3pt] coordinates {%s};" % (STYLE[p], " ".join("(%d,%.4f)" % q for q in sorted(rows[p]))))
            lines.append(r"\addlegendentry{%s}" % NAMES[p])
    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    open(os.path.join(OUT, "deletion.tex"), "w").write("\n".join(lines) + "\n")


def rank_table():
    """AUROC of the bound against the certified clearance, per key and pricer."""
    keys = (("Main key", ""), ("Audited key", "ah2-"), ("K2 (code-derived)", "k2-"))
    lines = [r"\begin{tabular}{@{}llrrrr@{}}", r"\toprule",
             r"Key & Pricer & AUROC & Cleared $\alpha{=}0.05$ & Wrong (mean / 95th pct.) & Cleared $\alpha{=}0.10$\\", r"\midrule"]
    for kname, pre in keys:
        first = True
        for p in ("choice-obj", "sonnetp", "b6", "b3", "freq", "uniform"):
            k = pre + p
            if k not in S or S[k]["apps"] < 100:
                continue
            c5, c10 = S[k]["certified"]["0.05"], S[k]["certified"]["0.1"]
            w = "--" if c5["wrong_mean"] is None else "%.1f\\%% / %.1f\\%%" % (100 * c5["wrong_mean"], 100 * c5["wrong_p95"])
            lines.append(r"%s & %s & %.3f & %.1f\%% & %s & %.1f\%%\\" % (kname if first else "", NAMES[p], S[k]["auroc_verdict"],
                                                                           100 * c5["cleared_mean"], w, 100 * c10["cleared_mean"]))
            first = False
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"
    lines.append(r"\end{tabular}")
    open(os.path.join(OUT, "rank_table.tex"), "w").write("\n".join(lines) + "\n")


def sizes():
    sz = S["choice-obj"]["sizes"]
    tot = sum(sz.values())
    lab = {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": r"$\geq$6"}
    lines = [r"\begin{tikzpicture}",
             r"\begin{axis}[ybar, width=0.98\linewidth, height=4cm, bar width=10pt, ymin=0, ymax=0.75,",
             r"  symbolic x coords={1,2,3,4,5,6}, xticklabels={%s}, xtick=data," % ",".join(lab[k] for k in "123456"),
             r"  xlabel={Facts in the receipt}, ylabel={Share of cleared sinks}, nodes near coords, nodes near coords style={font=\tiny},",
             r"  point meta=explicit symbolic, tick label style={font=\scriptsize}, label style={font=\small}]"]
    lines.append(r"\addplot[fill=blue!40] coordinates {%s};" % " ".join("(%s,%.4f) [%d]" % (k, sz.get(k, 0) / tot, sz.get(k, 0)) for k in "123456"))
    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    open(os.path.join(OUT, "sizes.tex"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    risk_coverage(["choice-obj", "sonnetp", "b6", "freq", "uniform"], "curve_main.tex", "main key")
    risk_coverage(["k2-choice-obj", "k2-sonnetp", "k2-b6", "k2-b3", "k2-uniform"], "curve_k2.tex", "K2")
    learning()
    deletion()
    rank_table()
    sizes()
    print("written:", sorted(os.listdir(OUT)))
