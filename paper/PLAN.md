# Evidence plan for the paper (ISSTA format: 18 pages without references and Data Availability)

Status: **HAVE** = data exists and the number is in the text; **RUNNING** = scheduled on the server; **TODO-LOCAL** = post-processing
we run on the laptop; **BUILD** = new pipeline to write; **NEEDS-PERSON** = only a person can do it; **CUT?** = candidate to drop.
Review criteria of the call: Importance, Originality, Soundness, Verifiability and Transparency, Presentation.

## Claims and the evidence each rests on

| Claim | Evidence | Status |
| --- | --- | --- |
| C1 Unsoundness through library holes is pervasive | RQ1: 12,274 of 17,830 methods unmodeled; FlowDroid without its summaries loses 86% (36 apps) | HAVE; extension to 80 apps RUNNING |
| C2 Priced receipts clear far more than a sound analysis at certified risk | RQ2: Table 2 (324 apps), 72.0% sound baseline, 40% of the rest at alpha 0.05 | HAVE |
| C3 The guarantee holds for every pricer and under every key | RQ2/RQ3: main key, K1 method- and class-level, K2, audited, human | HAVE for 5 pricers; panel of 5 more RUNNING |
| C4 Pricing is what makes receipts certifiable (counting clears 0%) | Table 2, counting row; 93% wrong at receipt size one | HAVE |
| C5 The key behind the clearances is sound enough | RQ4: audit passes, K2, person's 67 facts | HAVE; second rater NEEDS-PERSON |
| C6 Calibration must be per program | RQ7: verdict-level conformal 7.9%/14.3% vs target; grouped splits | PARTIAL: conformal on 324 apps TODO-LOCAL |
| C7 The result does not depend on calibration settings | RQ7: epsilon, split share, spread, grouped splits | HAVE (just computed) |
| C8 The method matters for real leaks | RQ10: TaintBench documented flows through library code | BUILD (data downloadable) |
| C9 Pricer quality holds beyond memorized APIs | RQ9: third-party libraries labeled with StubDroid | BUILD |
| C10 The analysis is a credible taint analysis | RQ5: 67% recall / 1% precision vs FlowDroid; entry-restriction does not fix it | HAVE; 80 apps RUNNING; a more precise variant CUT? |

## Placeholders in the paper

| Item | Where | Data source | Status |
| --- | --- | --- | --- |
| Fig. 1 pipeline diagram | Intro | none (draw in TikZ) | TODO-LOCAL |
| Fig. 2 receipt example | Example | `data/scale332` record | HAVE |
| Tab. facts (top facts and their labels) | Example | `data/audit*/` | TODO-LOCAL (assemble) |
| Fig. curve (coverage vs risk, all pricers) | Approach | per-delta lines of `app_ltt.py` | TODO-LOCAL |
| Tab. cost | Implementation | server logs | PARTIAL (panel costs RUNNING) |
| Tab. corpus | Setup | graphs, logs | PARTIAL (failed-app size distribution TODO-LOCAL) |
| Tab. fd-none | RQ1 | `bench/flowdroid_none_compare.py` | HAVE (40 apps); 80 RUNNING |
| Tab. main | RQ2 | `ltt_*` logs | HAVE |
| Tab. keys | RQ3 | logs | HAVE; panel columns RUNNING |
| Fig. deletion | RQ3 | `k1c_summary_*` | HAVE; panel RUNNING |
| Tab. panel | RQ3 | `panel_*.sh` | RUNNING |
| Tab. audit | RQ4 | `FINDINGS.md` | HAVE; kappa NEEDS-PERSON |
| Tab. fd (fidelity) | RQ5 | `flowdroid_compare.py` | HAVE (original and entry-restricted); 80 apps RUNNING |
| Tab. unit (calibration unit, sensitivity) | RQ7 | `analysis/sensitivity.py` | HAVE for the main pricer; per-verdict conformal and the panel TODO-LOCAL |
| Tab. wording | RQ8 | `panel_*.sh` | RUNNING |
| Tab. thirdparty | RQ9 | new pipeline | BUILD |
| Tab. taintbench | RQ10 | new pipeline | BUILD |
| Appendix tables (all deletion rates, per-app FlowDroid, per-key calibration) | Appendix | logs | HAVE |
| Proof details | Appendix | none | TODO-LOCAL (write) |
| Data availability, AI disclosure | end | none | needs the anonymous link, tool names, license |

## Scheduled on the server (unattended)

1. Pricer panel: Qwen3.8-27B, Qwen3.7-Flash, DeepSeek-V4-Flash (open weights), GPT-5.6-luna, Gemini-3.5-Flash-Lite, priced with
   verbalized probabilities (about \$7.5 in total); then, per pricer: main key, whole-class deletion at 50% and 75% with 3 seeds, K2.
2. Wording ablation: Jev with the "taint" and "choice" wordings on the current method list, main key.
3. FlowDroid on 40 more apps, with and without its library summaries (80 in total).

## To build next

- RQ10 TaintBench: download the 39 apps and the documented findings; build graphs; price new methods; compare, per documented flow,
  our verdict with holes closed, with holes open, and the receipt price; report whether any documented leak is wrongly cleared at the certified threshold.
- RQ9 third-party libraries: StubDroid on Gson, Guava, Commons-Lang/IO and Jsoup; about 1,500 questions; price with Jev and the panel; AUROC, ECE.

## Needs a person

- A second rater on 20 audit facts for an agreement statistic (kappa).
- The anonymous artifact link, the license, the exact names of the AI tools for the disclosure.
- Decision: whether to cut the closing-the-holes experiment (it ended in a fallback: no privacy leak found) or give it half a page.

## Candidates to cut if space or time runs out

Per-app FlowDroid table (appendix only), the wording ablation (one sentence), the entry-restricted variant (one sentence), RQ6 cost (merge into the implementation section).
