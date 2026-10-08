# Soundiness with Receipts: an overview for newcomers

This document explains the project from scratch: the problem, the gap in existing work, our idea, what we built, the
experiments, what they show, where things stand, and where to find everything in the repository.
Paper title: "Soundiness with Receipts: Certified Miss-Risk for Unsound Static Analyses" (target: ISSTA 2027).
Written 2026-10-07, updated 2026-10-08. Main setting: our analysis uses FlowDroid's library models, and holes are only the methods FlowDroid does not model. Numbers are from the main answer key (the rubric key: FlowDroid's models plus the labels on which two LLM families agree under a written definition) unless stated otherwise.

---

## 1. The problem in plain words

A *taint analysis* checks whether sensitive data (a phone number, the device ID, a location) can flow from a *source*
(the call that produces it) to a *sink* (a call that lets it leave the app: network, SMS, a log, a file).
If no path exists, the tool says "no leak" for that sink. We call that a *clean verdict*.

Android apps call thousands of library methods (Android framework, Java library) whose code the analysis does not read.
For each such call the tool must know whether data passes through it: does `StringBuilder.toString()` pass its contents
to the result? Does `String.equals(x)` copy `x` anywhere? Tools answer with *models* (summaries). FlowDroid, the standard
Android taint analysis, ships hand-written models for about 350 classes. **For every method without a model, the tool
silently assumes that no data passes.** So a "no leak" verdict can be wrong, and the tool never says how likely that is.

How big is this? When FlowDroid is run without its models, 82% of the leaks it reports disappear, so models matter. But
they are incomplete: in our corpus of 324 apps, 12,274 of the 17,830 library methods on source-to-sink paths have no
FlowDroid model, and even with all of FlowDroid's models a third of the real leaks (22,888 sinks) pass only through such
unmodeled methods, so an analysis relying on the models reports them as clean.

Analyses that are "sound except for documented gaps" are called *soundy*. What was missing is a way to say how often
those gaps actually cause a wrong verdict.

## 2. The gap: why existing answers are not enough

| Existing answer | What it does | Why it is not enough |
| --- | --- | --- |
| Sound analysis | assume every unmodeled method passes all data | catches the missed leaks but adds false alarms to 298 of 307 apps (5,318 in total, about 18 per app), with no ranking |
| More library models (hand-written, StubDroid from code, Atlas, or a language model as in IRIS/SemTaint) | fill in the missing summaries | every model can be wrong, and a verdict computed from a model taken as fact has no error measure |
| List the assumptions (Bastani et al. 2015: minimal cuts checked by a person) | tell the user which facts a verdict rests on | says *what* was assumed, not *how likely* it is to fail; every verdict still needs a person. Counting assumptions does not help: clearing every verdict that rests on one assumption leaves a wrong clearance in 93% of apps |

None of them tells the user: "this clean verdict is wrong with probability at most X, and that promise is checked".

## 3. Our idea, step by step (with the paper's example)

App `de.luhmer.owncloudnewsreader` (a Nextcloud news reader) has two clean verdicts; FlowDroid models neither method:
- **Verdict A** (`ContentResolver.insert`, data written to a content provider) depends on one library fact:
  `ContentValues.put` stores its argument. This flow is real, so verdict A misses a leak, and so does FlowDroid.
- **Verdict B** (a `Log.d` call) depends on one library fact: registering a listener on `TextToSpeech` copies data into
  the listener. That never happens, so verdict B is correct.

A sound analysis flags both (B is a false alarm). Counting assumptions sees "1" for both. Our approach separates them:

1. **Holes.** Every possible library flow (each argument or the receiver of a library call to each value that could
   receive data) is a *hole*. The analysis runs with all holes open, building a *flow graph*.
2. **Receipt.** For each clean verdict that depends on holes, the *receipt* is the smallest set of holes such that, if
   none of them is real, the verdict is correct (a cut in the flow graph). Verdict A's receipt is the `CharBuffer`
   fact; B's is the `String.equals` fact.
3. **Prices.** A *pricer* (a language model) gives each hole a probability of being real: 0.88 for the `ContentValues`
   fact, 0.10 for the `TextToSpeech` fact.
4. **Bound.** The sum of the prices on a receipt bounds the probability that the verdict is wrong. This needs no
   assumption that library flows are independent. The cheapest receipt is a *minimum cut*, computed by max-flow, and we
   prove that no smaller bound can be derived from the individual prices.
5. **Certified threshold.** A verdict is cleared if its bound is below a threshold. The threshold is *certified* on a
   sample of other apps with an exact statistical test (Learn-then-Test), so that with confidence 1-eps, a new app gets a
   wrong clean verdict with probability at most alpha. We call this *(alpha, eps)-soundiness*. Here the certified
   threshold is 0.2: B (0.10) is cleared, A (0.88) is reported as a possible leak.
6. **Checking facts (optional).** Receipts name facts a person can check. One fact often sits in many receipts, so
   checking a few well-chosen facts clears many verdicts.

The key property: **the guarantee holds whatever the pricer.** A bad pricer clears less; it does not create wrong
clearances beyond the certified rate. The pricer only decides *how much* is cleared.

## 4. Contributions and what is new

1. **A measurable notion of soundiness**, (alpha, eps)-soundiness: per program, how often an analysis wrongly clears a
   verdict, with a certified bound.
2. **Priced receipts**: a per-verdict bound on the chance of a missed flow, without independence assumptions, proved to
   be the tightest possible from individual probabilities; plus a certified threshold valid for any pricer.
3. **Budgeted checking**: choosing which library facts a person should verify, without looking at any answer, so each
   check clears as many verdicts as possible.
4. **An evaluation** on 324 benign and 33 malicious apps, several answer keys, ten pricers and FlowDroid itself,
   including the cases where the approach clears little.

What is new compared with prior work: each verdict gets *both* an explanation (which facts) and a risk (a probability),
and the risk is *certified on new programs* rather than trusted. The certificate is per *program*, which matters: the
common per-verdict alternative (conformal selection) leaves wrong clearances in half of the apps at the same target.

## 5. How it is built

- **Fact extraction**: Soot reads each APK (`extract/Facts.java`), producing Datalog facts.
- **Analysis**: a Souffle Datalog program (`analysis/taint.dl`) computes points-to and taint with every hole open and
  stores the relevant flow graph per app (a few MB, `.npz`).
- **Receipts and bounds**: `analysis/evaluate.py` runs max-flow/min-cut per sink, for any pricer and answer key.
- **Pricing**: Jev (a commercial calibrated yes/no service, our main pricer, ~$0.4 for all methods), Sonnet 5 (~$16),
  five cheaper LLMs, and simple baselines (counting, frequency prior, a classifier, LLM answers taken as fact).
- **Calibration**: `analysis/app_ltt.py` (certified threshold, 200 random half splits of the apps).
- Heavy runs happen on a lab server (8 cores, 62 GB); see `~/server_connect_pku.md` and `bench/SERVER_RUNBOOK.md`.

## 6. Experiments and what they show

Metric names: the **hard slice** = the 5,318 leak-free sinks that depend on unmodeled library flows (a sound treatment of
unmodeled methods cannot clear them). **Cleared** = share of the hard slice we clear. **Apps wrong** = share of held-out apps with at least one
wrong clearance (must stay below alpha).

| # | Question | What we did | Result | What it shows |
| --- | --- | --- | --- | --- |
| RQ1 | Do clean verdicts depend on unmodeled library flows? | FlowDroid with and without its models on 80 apps; our corpus with FlowDroid's models; TaintBench; holes inside FlowDroid | FlowDroid loses 82% of its leaks without models; with all of FlowDroid's models, 22,888 real leaks (a third) pass only through unmodeled methods; opening them adds 5,318 false alarms in 298 of 307 apps; FlowDroid with holes: 58 extra sinks, 43 FlowDroid-confirmed receipts | models matter and are incomplete; the gap is large |
| RQ2 | How much do receipts clear at a certified risk? | 307 apps, alpha 0.05 | Jev clears 49% of the hard slice with 0.9% of apps wrong (37% at alpha 0.02); counting clears 0%; LLM-as-fact has no risk control (up to 7.7% of apps wrong); per-verdict conformal misses its own target (6.6% at 5%) and leaves wrong clearances in 17% of apps | prices make receipts useful; per-program calibration is needed |
| RQ3 | Does the guarantee survive other answer keys? | deletion keys (no LLM labels), StubDroid key, GPT key, human-audited key, label noise, rubric key | apps wrong at most 2.6% under every key; cleared share varies (Jev 48% under the main key, 40% under the Sonnet-only key, 23% under the GPT key, 8-14% under a noisy key) | validity is robust; how much is cleared depends on how strict the key is |
| RQ3b | Is the key reliable? | Sonnet vs GPT labels; relabeled with a written definition | short prompt: kappa 0.62; with the written definition: kappa 0.80, the models match a person's source checks on 92% and 93% of 60 facts, and 95% where both models agree | the earlier disagreement came from a vague question, now fixed |
| RQ4 | What makes a pricer useful? | 7 LLM pricers, ranking analysis, question wording | cheap models answer too confidently and clear ~0-4% at alpha 0.05; the classifier and Sonnet rank better on average than Jev but clear much less; stating the flow rule in the question nearly triples Jev's clearance | a pricer must give low prices only to flows that are really absent; the guarantee never broke |
| RQ5 | Does checking a few facts help? | rank facts without labels, let the key answer the top K, recertify | 25 checks: 49% to 63%; 100 checks: 78%; 100 random checks: 52% | receipts make human effort efficient |
| RQ6 | Does a threshold certified on benign apps hold on malware? | certify on F-Droid, apply to 23 TaintBench apps | 0 of 23 apps wrong (Jev, Sonnet); with FlowDroid's models only 6 documented leaks need unmodeled flows, all callbacks / inter-component calls / reflection, which our flow definition excludes | transfer holds against our key; few malware leaks depend on the flows we price |

Results that did **not** work out (reported honestly, mostly not in the paper):
- **Our analysis is weaker than FlowDroid**: it reaches 58% of FlowDroid's leaks, ~1% precision. The guarantee is about
  library flows relative to whatever analysis produces the flow graph.
- **Receipts on FlowDroid** work but could not be certified: too few apps finished within FlowDroid's time limits.
- **Intent (inter-component) holes** work as a second kind of hole but found no new documented malware leaks.
- **Choosing FlowDroid's next library models by receipts** did not beat simple baselines (null result).
- **Cheap LLM pricers** were nearly useless (valid but clear little).

## 7. Where things stand

- The paper is restructured in the lab's style, 16 of 18 pages, compiles cleanly: `paper/main.pdf`.
- The paper now uses the rubric key as main key (decided 2026-10-08). Still running: the wording ablation under it.
- Mock-review estimate: about 25-30% acceptance chance now; about 45% after three planned fixes (holes only where
  FlowDroid has no model; certify on FlowDroid; show analyst effort saved).
- Full list of open items: `paper/REMAINING_WORK.md`; detailed plans for the reviewer fixes: `paper/REVIEW_FIXES.md`.

## 8. Repository guide

### Documents (read in this order)
| File | What it is |
| --- | --- |
| `OVERVIEW.md` | this file: the whole project for a newcomer |
| `HANDOFF.md` | for whoever continues the work: running jobs, rules, code map, gotchas |
| `paper/REMAINING_WORK.md` | the current to-do list, ranked, with who must decide what |
| `paper/REVIEW_FIXES.md` | step-by-step plans for the three fixes that most raise acceptance chances |
| `FINDINGS.md` | the research log: every experiment with numbers, in date order (sections 1-22b); the source for paper numbers |
| `paper/main.tex`, `paper/sections/*.tex` | the paper; `paper/main.pdf` is the compiled version |
| `paper/PLAN.md` | historical evidence plan (2026-10-05); superseded by `REMAINING_WORK.md` |
| `paper/my_lab_papers/` | the lab's past papers used as style models |
| `AUDIT_TASK.md`, `AUDIT_RECHECK.md`, `AUDIT_SAMPLE_NO.md`, `AUDIT.md` | instructions given to the people checking library facts (the human audit) |
| `Related work.md`, `ISSTA 2027 plan.md`, `llm_convo.md` | early planning notes (historical) |
| `~/server_connect_pku.md` (home directory, not in the repo) | how to reach the lab server (VPN, ssh) |
| `bench/SERVER_RUNBOOK.md` | how the server builds were run |

### Code
| Path | What it does |
| --- | --- |
| `extract/Facts.java`, `extract/Manifest.java` | Soot fact extraction from APKs; manifest components (for Intent holes) |
| `extract/k2/` | StubDroid runs that produce the code-derived answer key (K2) |
| `analysis/taint.dl` | the Datalog taint analysis with holes; `taint_entry.dl` (entry-point restricted) and `taint_icc.dl` (Intent holes) are generated variants |
| `analysis/run_android.py` | builds flow graphs for many apps (env vars select app lists, source/sink list, Datalog variant) |
| `analysis/evaluate.py` | receipts and bounds for every sink; selects pricer and answer key by name prefix (`k2-`, `gk-`, `rk-`, `k1c-`, `kn1-`, ...) |
| `analysis/app_ltt.py` | the certified threshold (Learn-then-Test) over random app splits |
| `analysis/sensitivity.py`, `analysis/conformal.py` | calibration sensitivity; per-verdict conformal comparison |
| `analysis/verify_select.py`, `analysis/verify_summary.py` | budgeted checking (RQ5) |
| `analysis/taintbench_compare.py` | TaintBench documented leaks vs our verdicts (RQ6) |
| `analysis/paper_stats.py`, `paper/make_figs.py` | statistics and pgfplots figures for the paper |
| `probes/run_jev.py`, `probes/run_sonnet_price.py`, `probes/run_oracle.py`, `probes/price_icc.py` | pricers and answer-key labeling (OpenRouter, or Claude Code / Codex via `probes/cli_llm.py`) |
| `bench/flowdroid_*.sh`, `bench/flowdroid_compare.py` | FlowDroid runs and comparisons (RQ1) |
| `bench/fd_receipts.py`, `bench/fd_receipts_eval.py` | receipts computed inside FlowDroid |
| `bench/queues/*.sh` | every unattended server chain (one script per experiment) |

### Data
| Path | What it holds |
| --- | --- |
| `data/holes_android_fw.jsonl` | every library method with its candidate flows and labels (the hole list) |
| `data/jev_holes_android_fw_<pricer>_r0.jsonl` | prices per method (`choice-obj` = Jev main; `sonnetp` = Sonnet; panel tags `q27`, `qflash`, ...) |
| `data/oracle-*.jsonl` | language-model labels for the answer keys (`sonnet5-unk`, `gpt61-unk`, `rubric-sonnet5`, `rubric-gpt61`) |
| `data/k2_labels.json` | StubDroid-derived labels (K2) |
| `data/audit/` | human audit sheets (`human_source_check.csv`, `human_sample2.csv`, ...) |
| `data/scale332/` | local copy of the main per-sink results |
| server `~/receipts/data/` | everything large: flow graphs (`graphs*/`), per-sink results (`android_*.jsonl`), FlowDroid outputs, chain logs (`*_chain.log`) |

### Building the paper
`cd paper && latexmk -pdf main.tex` (figures are generated into `paper/figs/` by `paper/make_figs.py` from
`data/paper_stats.json` and the deletion summaries).

## 9. Glossary
- **Source / sink**: call that produces sensitive data / call that lets data leave the app.
- **Clean verdict**: the analysis says no source reaches this sink.
- **Hole**: a candidate library flow the analysis does not model.
- **Hole-dependent**: a clean sink that a source would reach if all holes were open.
- **Hard slice**: hole-dependent sinks that truly never leak; a sound analysis cannot clear them.
- **Receipt**: the cheapest set of holes a clean verdict assumes absent (a min-cut).
- **Pricer**: the model that gives each hole a probability of being real.
- **Bound**: the sum of the receipt's prices; an upper bound on the chance the verdict is wrong.
- **Certified threshold**: the bound level up to which verdicts are cleared, chosen by an exact test on other apps.
- **(alpha, eps)-soundy**: with confidence 1-eps, a new app gets a wrong clearance with probability at most alpha.
- **Answer key**: what we treat as the truth about library flows for evaluation (several, built differently).
- **Main / K1 (deletion) / K2 (StubDroid) / GPT / rubric / audited key**: the answer keys described in RQ3.
- **Jev**: the commercial calibrated yes/no service used as the main pricer.
