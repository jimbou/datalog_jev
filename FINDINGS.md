# Soundiness with Receipts — feasibility findings (2026-09-26)

Working idea (from `llm_convo.md`): an unsound Datalog analysis skips "holes" (library bodies,
reflection, callbacks). Enumerate candidate hole facts, price each with Jev, and bound every clean
verdict's miss risk by the cheapest set of candidate facts whose removal blocks all derivations
(min-cut; union bound, no independence assumed). End-to-end validity comes from conformal
calibration over programs.

**Verdict: feasible, with a certified result.** On 103 real Android apps, program-level
Learn-then-Test certifies acceptance of **41% of clean verdicts** while keeping the per-app
false-accept risk at or below 10% (held out: 1.0%). See §9. Three things made it work: stating the
flow convention in Jev's question (§8), type-filtered Soufflé analysis to scale, and silver labels
for unmodeled framework methods. Total spend: about $5.40 of OpenRouter credit ($4.62 left).
§§2–7 are the first-round results on 14 apps, kept for the record.

## 1. Infrastructure built

| Piece | Where | Notes |
| --- | --- | --- |
| Jev access | `probes/jev_call.sh`, `probes/run_jev.py` | OpenRouter `api/alpha/decisions`, key `OPENROUTERS_MINE`, ~$0.00002/call, ~1 s |
| LLM baseline | `probes/run_llm.py` | P(yes) from token logprobs (Qwen3-30B via OpenRouter) |
| Soufflé 2.5 | `tools/souffle.sh` | unpacked .deb, no root |
| Soot fact extractor | `extract/Facts.java`, `extract/extract_apks.py` | .class dirs or APKs → TSV facts |
| Ground truth ("completed analyzer") | `data/stubdroid/*.xml` | FlowDroid manual summaries, 356 classes |
| JDK atom calibration set | `probes/build_libflow.py` → `data/libflow.jsonl` | 1,525 methods, 3,971 atoms (1,801 true) |
| OWASP pipeline | `analysis/taint.py`, `analysis/pipeline_eval.py` | 1,698 taint-category tests |
| Android pipeline | `analysis/taint.dl`, `analysis/run_android.py`, `analysis/android_eval.py` | 24 F-Droid apps (14 analyzed) |

Candidate menu per library method: every `src → tgt` pair with src ∈ {arg_i, this} and tgt ∈
{ret, this, mutable arg_j}. A flow is true iff the FlowDroid summary has it (field paths collapsed
to their base object).

## 2. Jev as a pricer (JDK atoms, `probes/analyze.py`)

| Scorer | AUROC | ECE | False atoms priced < 0.05 | True rate among p < 0.05 | Cost / 4k atoms |
| --- | --- | --- | --- | --- | --- |
| Jev Noul, "taint" wording | 0.92 | 0.10 | 1.8% | 0% (valid, loose) | $0.03 |
| Jev Noul, "may flow" wording | 0.94 | 0.13 | 1.0% | 0% | $0.03 |
| **Jev Choice {yes, no}** | 0.92 | **0.038** | **27%** | 3.6% (mean p 2.2%: slightly overconfident) | $0.03 |
| Qwen3-30B logprobs | 0.70 | 0.26 | 27% | **24%** (unusable) | $0.015 |

- **Noul answers have a price floor on flow questions** (about 0.035), and it's specific to the
  question: absurd statements get 0.01. The floor is conservative, so bounds stay valid, but it
  makes them loose.
- **Choice answers are sharp but slightly overconfident at the low end.** For flows into the
  return value, 15% of atoms priced below 0.1 are true. So raw per-fact validity can't be claimed;
  validity has to come from end-to-end calibration, as the convo concluded.
- **Repeat stability:** the standard deviation across 3 repeats is about 0.01, so averaging repeats
  buys little.
- **A cheap general LLM at the same cost is far worse** (AUROC 0.70, 24% true among its "certain
  no" answers). That's a clean argument for Jev: calibrated low-end prices, not cheapness, because a
  cheap LLM costs about the same.
- **Label noise in FlowDroid cuts both ways.** It omits `new BigDecimal(String)` arg0→this and
  `URI.getHost()` this→ret. It includes debatable conventions like `Random.nextInt()` this→ret.

## 3. OWASP Benchmark: the wrong benchmark (important negative result)

- The analysis with FlowDroid summaries finds all 902 real vulnerabilities, while the analysis with
  no library model finds only 109 of the 1,390 flows it reports. So the holes matter.
- **But every clean verdict is clean for code reasons.** None of OWASP's 308 clean cases would
  become a flow if some library fact were true, so every bound is exactly 0.
- **Lesson:** injection micro-benchmarks never test the question this idea answers. The paper needs
  real apps, or a new benchmark built by simulating holes.

## 4. Real Android apps: the idea works (`analysis/android_eval.py choice`)

Setup: 24 F-Droid apps (internet access plus location, contacts, or phone permissions); app code
and bundled libraries analyzed as code; `android.jar` framework methods are the holes;
FlowDroid's `SourcesAndSinks.txt` gives sources and sinks. The analysis is whole-app and
context-insensitive in Soufflé, with Andersen points-to; bounds come from scipy max-flow.

Hole landscape across the 24 apps:
- 12,529 framework methods carry candidate atoms. FlowDroid models 3,877 of them (1,936 with
  summaries, 1,941 implicit no-flow).
- **8,618 methods are completely unmodeled** (25.7k atoms, 352k call sites). This is FlowDroid's
  real unsoundness.

14 apps analyzed (10 hit the 14 GB memory cap):

- 4,000 reachable sinks. 1,140 are reachable through code alone, and 2,860 depend on hole facts.
  Truth is determined for 2,272 of those (1,755 real flows, 517 clean).
- **Cuts on clean sinks are small:** 213 need 1 fact, 173 need 2, 50 need 3, with a tail beyond.
- Bound quantiles (10/25/50/75/90%), Choice prices: clean sinks 0.04 / 0.08 / 0.16 / 0.23 / 0.98;
  real flows 0.98 / 1.0 / 1.96 / 3.13 / 7.33.

Pipeline at τ = 0.3 (report an alarm if reachable using candidates priced ≥ 0.3); Choice prices:

| Risk threshold δ | Clean sinks accepted | False accepts | FDR |
| --- | --- | --- | --- |
| 0.01 | 3.3% | 0 | 0 |
| 0.05 | 15.9% | 0 | 0 |
| 0.10 | **30.6%** | 0 | 0 |
| 0.20 | **62.7%** | 1 | 0.003 |

Recall of reported alarms is 99.7% at 95.8% precision. With Noul prices, acceptance is 2.1% at
δ = 0.10 and 32.5% at δ = 0.20, again with 0 false accepts. **Choice prices give much more power
for the same validity.**

Kill criterion from the convo: "at δ = 0.05, if fewer than a fifth of truly clean verdicts are
accepted, the idea is dead." Raw Choice prices reach 15.9% at 0.05 and 30.6% at 0.10. That's
borderline at 0.05 before any recalibration, and the isotonic remapping measured in §2 roughly
doubles the share of false atoms priced below 0.05.

## 5. Caveats and threats (be honest in the paper)

1. **Truth is relative to FlowDroid's summaries.** 588 of the 2,860 hole-dependent verdicts depend
   on unmodeled facts and were left out. That exclusion may bias the result, because verdicts that
   touch unmodeled facts are probably harder.
2. **Zero false accepts is not a guarantee.** Only 517 clean and 1,755 real verdicts, from 14 apps
   and not exchangeable per program. The conformal layer (programs as units) is not built yet.
3. **Scalability:** context-insensitive points-to over bundled libraries runs out of memory on 10
   of 24 apps. Fix it with type filtering, a cheaper heap abstraction, compiled Soufflé, or by
   summarizing bundled libraries.
4. **Framework callbacks are a second, unmodeled hole:** framework-declared virtual calls never
   dispatch into app code. They're a natural second hole type (the convo mentioned lifecycle
   callbacks), and they're not priced yet.
5. **Per-call-site max-flow counts a shared summary fact once per call site.** The bound stays
   valid but looser; the exact version (a labeled cut, NP-hard) could only tighten it.
6. **JDK/Android methods are heavily memorized.** Jev will do worse on obscure third-party
   libraries, so evaluate on bundled-library holes (hide their bodies) too.

## 6. Novelty check (September 2026)

- **Xin Zhang's group** (NESA OOPSLA'25, Bayesian+LLM alarms OOPSLA'26b, PLDI'26 confidence,
  exploration–exploitation OOPSLA'26a, Bayesian fuzzing POPL'26): all about the *precision* of
  sound analyses or alarm ranking. **Nothing bounds the unsoundness of unsound analyses.** Still
  the obvious competitor, and in your lab.
- **Böhme and colleagues:** residual risk from *testing* (STADS, Good-Turing; ICSE'26
  dependency-aware DP; arXiv 2607.17061 on user encounter bounds). Sampling-based, no static
  structure: cite and contrast.
- **LLM taint work** (IRIS, adaptive source/sink identification arXiv 2511.04023, LLM-agent
  Android taint arXiv 2608.24269 with F1 0.96 on DroidBench): these plug in or replace
  specifications, with **no uncertainty quantification or per-verdict risk.**
- **Specification inference** (Merlin PLDI'09, Seldon PLDI'19, StubDroid, DAInfer+, Symmaries):
  they produce specifications, not verdict-level risk.
- **Praline** (probabilistic Datalog bounds) and **PSP** (ASE'23): discussed in the convo. Praline
  is the inference baseline; PSP is the closest in spirit.

**The open gap remains: a per-verdict, checkable risk certificate for an unsound analysis's clean
verdicts.** Move fast; the Bayesian program analysis groups could get there next.

## 7. How to frame the paper

**Title:** *Soundiness with Receipts: Certified Miss-Risk for Unsound Static Analyses*

**Claim:** each clean verdict comes with (a) a receipt, the set of assumed-absent library behaviors
it depends on, (b) the tightest distribution-free bound given per-fact prices (exact via max-flow),
and (c) an acceptance rule with FDR control, calibrated over programs.

**Evidence to lead with:**
1. Unsoundness is pervasive and invisible: 8.6k unmodeled framework methods across 24 apps.
2. Receipts are small: most clean verdicts depend on 1–2 facts, so they're human-auditable.
3. The bounds separate real flows from clean sinks (medians 1.96 vs 0.16).
4. Useful acceptance rates at zero observed false accepts (31% at δ = 0.10, 63% at δ = 0.20).
5. The pricer matters: Jev versus a same-cost LLM, and Choice versus Noul prices.

Also: existing benchmarks (OWASP) can't exercise this; propose hole simulation on real apps as the
evaluation methodology.

**Reframe Jev's role:** not "calibration is load-bearing". Calibration drives *power*, validity comes
from the conformal layer, and Jev is the cheapest well-ranked, low-tail-calibrated pricer we tested.

## 8. Round 2 findings (same day, later)

**Label fix.** FlowDroid models builder-style methods (`StringBuilder.append`, `JSONArray.put`, …)
as "argument → receiver, receiver returned by alias". The first collapse dropped the composition.
It's fixed in `build_libflow.close_flows`: 146 JDK and 168 Android atoms flipped to true. With the
fix, Jev Choice reaches AUROC 0.937 and ECE 0.030.

**Silver oracle.** On 300 FlowDroid-modeled Android methods (776 atoms), Claude Sonnet 5
(`probes/run_oracle.py`) agrees with FlowDroid on 94.3%, with errors balanced (23 / 21). It
labeled 2,954 unmodeled framework methods that lie on relevant paths, for $2.41. With silver
labels, truth is determined for 99.7% of hole-dependent verdicts (was 80%).

**Flow semantics must be stated in the question (key lesson).** Silver labels exposed false
accepts. Almost all involve getters on a tainted receiver (`MenuItem.getItemId`,
`MotionEvent.getAction`, `Window.findViewById`, `Enum.name`). FlowDroid and the oracle use
object-granularity taint, and Jev read "derived data" more narrowly (prices 0.02–0.19). Restating
the convention in the question fixes the low end on JDK atoms:

| Jev wording | AUROC | True rate at p < 0.05 | True rate at p < 0.10 | False atoms below 0.05 |
| --- | --- | --- | --- | --- |
| choice | 0.937 | 3.6% | 4.2% | 29% |
| **choice-obj** (object convention stated) | 0.941 | **0 / 346** | **0.6%** | 17% |

**Verdict-level conformal selection is not valid here; program-level calibration is required.**
Leave-one-app-out conformal selection (`analysis/conformal.py`, BH with conformal p-values) gave
realized FDR 7.9% at α = 0.05 and 14.3% at α = 0.10. Verdicts within an app share facts and
structure, and apps differ, so verdicts are not exchangeable. This confirms the convo's point:
the exchangeable unit must be the program. `analysis/app_ltt.py` implements Learn-then-Test with
apps as units (per-app family-wise false-accept risk, exact binomial test, fixed sequence over δ).
It needs about 22 or more calibration apps with no false accepts to certify α = 0.1, which is why
the corpus was scaled to 130 apps.

**Scalability.** Type-filtered points-to (`VarType` facts plus the framework hierarchy) cut
points-to facts 1.5–3× and made previously failing apps run (`net.dcnnt`: 80 s). About 1 in 6
apps still exceeds 12 GB. The driver now runs apps in parallel (`JOBS`) and records failures in
`data/android_failed.txt`.

## 9. Full-corpus result: 103 apps, certified at the program level (headline)

Corpus: 130 F-Droid apps (24 original plus 106 small apps with internet access and a sensitive
permission); 103 analyzed (26 exceed 12 GB). 30.4k reachable sinks, 22.3k hole-dependent,
22.0k with determined truth (FlowDroid labels plus Sonnet 5 silver labels for unmodeled methods),
about 6.4k clean. 16,323 framework methods priced. Clean-sink cuts: about 45% need 1 fact and
about 20% need 2.

Learn-then-Test with apps as units (`analysis/app_ltt.py`, α = 0.1, ε = 0.1, 200 random 50/50
app splits, held-out numbers):

| Jev pricing | Certified δ | Held-out apps with any false accept | Clean verdicts accepted |
| --- | --- | --- | --- |
| Noul "taint" | 0.15 | 0.0% | 17.4% |
| Choice | 0.03 | 0.0% | 15.9% |
| **Choice, object convention stated** | **0.20** | **1.0%** | **41.1%** |

At α = 0.05 (ε = 0.1), the object-convention prices certify δ = 0.15–0.2 with 35% power. With
the original Choice wording, a single widely bundled fact (`Rating.getRatingStyle` this→ret,
priced 0.05, in 32 apps through support-library code) sits behind a cliff from 0 to 33 apps with
false accepts at δ = 0.05. Stating the convention removes it: 0 of 102 apps have a false accept up
to δ = 0.15.

The guarantee reads: *for a new app drawn like the calibration apps, the probability that any
accepted clean verdict is actually a real flow (relative to the completed analyzer) is at most
10%, with 90% confidence.* α = 0.05 at ε = 0.05 or α = 0.02 cannot be certified with about 51
calibration apps (0.95^51 > 0.05). That needs 60+ calibration apps, which is purely a matter of
corpus size.

**New threat: bundled library code is shared across apps**, so apps are not fully independent
units. Deduplicate bundled libraries (analyze them once, or treat library versions as separate
units) before claiming exchangeability.

**Kill criterion, revisited:** with the certified program-level procedure, 41% of clean verdicts
are accepted at α = 0.1 and 35% at α = 0.05, both above the convo's 20% bar.

## 10. Baselines on the full corpus (2026-09-27)

**Sound baseline B2 (every hole is a flow).** Over the 103 apps, B2 already clears 77.9% of
leak-free sinks with a non-constant argument (85.7% over all sink calls), at zero risk. The
headline 41% is over the remaining hard slice: leak-free sinks that are reachable when every
hole is on (22.0% of leak-free sinks). Ours clears B2's share plus 41% of the hard slice, 86.9% of
leak-free sinks in total. The paper must state the 78% up front and lead with the hard slice.

**Pricing is what makes receipts certifiable.** App-level LTT on the hard slice, held-out
numbers over 200 splits (`analysis/evaluate.py` + `analysis/app_ltt.py`, graphs in `data/graphs/`):

| Pricer | Cleared, α = 0.1 | Cleared, α = 0.05 | Held-out apps with a wrong clearance |
| --- | --- | --- | --- |
| B2 sound | 0% | 0% | 0% |
| B4 unweighted cut / flat price (Bastani-style) | 0% | 0% | 0% |
| B7 frequency prior (package × flow kind, leave-method-out) | 9.0% | 8.9% | 0.4% / 0% |
| Jev, flow rule stated | **41.3%** | **34.8%** | 0.9% |

Counting guesses fails completely: clearing receipts of size 1 already gives a wrong clearance in
100 of 103 apps. Receipt size says nothing about which guess is safe. This answers the
Bastani/Zhu prior-art objection: the cut is old, but only calibrated prices make it certifiable.

**Storage.** Soufflé now writes to a temporary directory; each app keeps only a compressed graph
(`data/graphs/*.npz`, 104 apps in 69 MB, replacing an 18 GB cache). Any new pricing or ablation is
post-processing in minutes (`evaluate.py PRICING`).

## 11. Deletion benchmark K1: the guarantee holds with no LLM in the answer key (2026-09-27)

Truth = FlowDroid's models. In each run a random share of the FlowDroid-modeled framework methods
is deleted (`evaluate.py k1-<rate>-<seed>-<pricing>`): deleted methods become Jev-priced holes, the
rest become fixed code edges, unmodeled methods mean no flow (as in FlowDroid itself). Apps are the
calibration unit; 200 random 50/50 splits per run; mean over 5 seeds (`analysis/k1_summary.py`).

| Deleted | Hard-slice verdicts (clean / real) | α = 0.10: wrong clearances (worst seed) | α = 0.10: cleared | α = 0.05: wrong clearances (worst seed) | α = 0.05: cleared |
| --- | --- | --- | --- | --- | --- |
| 10% | 807 / 2,548 | 0.9% (2.4%) | 87.2% | 0.4% (1.3%) | 81.2% |
| 25% | 1,703 / 3,827 | 1.5% (2.6%) | 82.0% | 0.7% (1.6%) | 77.4% |
| 50% | 3,254 / 8,342 | 1.4% (2.2%) | 75.5% | 0.7% (1.0%) | 68.6% |

The uniform price (B4, counting guesses) clears 0% in every run. The observed error stays well
below α in all 15 runs, and α = 0.05 is certifiable here with the same ~51 calibration apps.
Power is higher than on the main key (41%) because deleted methods are ones FlowDroid chose to
model, i.e. well-known APIs; the main key also contains never-modeled methods. Report both keys
and name this difference.

## 12. Corrections found while starting G3 (2026-09-27, rerun in progress)

1. **Static-factory labels.** FlowDroid models flows of static factories (`Uri.parse`,
   `Bitmap.createBitmap`, `ComponentName.createRelative`, 65 methods) into a Field typed with the
   return type, i.e. the returned object. The collapse now maps that to `ret`; 55 Android labels
   changed.
2. **Source/sink list.** The parser read FlowDroid's disabled entries (lines starting with `%`,
   mostly inter-component sources like `getIntent`/`getExtras` and sinks like `startActivity`) as
   active: 173 sources / 224 sinks instead of the default 84 / 193. All Android results in §4 and
   §9–11 used that extended list. Graphs and all evaluations are being rebuilt with the default
   list; the tables above will be replaced.

**Corrected results (default FlowDroid source/sink list, 102 apps; these replace §9–11).**
The sound baseline B2 clears 70.8% of leak-free sinks (with a non-constant argument); the hard
slice is 29.1% (8,785 clean verdicts). App-level LTT, held-out, 200 splits:

| Pricer | Cleared, α = 0.1 | Cleared, α = 0.05 | Held-out apps with a wrong clearance |
| --- | --- | --- | --- |
| B4 counting guesses | 0% | 0% | 0% |
| B7 frequency prior | 7.5% | 6.2% | 1.4% / 0.2% |
| Jev, flow rule stated | **36.9%** | **33.0%** | 1.0% / 1.0% |

Total leak-free sinks cleared: 81.5% (α = 0.1) and 80.4% (α = 0.05), against 70.8% for B2.
Clearing size-1 receipts by counting gives a wrong clearance in 92 of 102 apps.

Deletion benchmark K1 (no LLM in the key), mean over 5 seeds:

| Deleted | α = 0.1: wrong clearances (worst) | α = 0.1: cleared | α = 0.05: wrong clearances (worst) | α = 0.05: cleared |
| --- | --- | --- | --- | --- |
| 10% | 0.4% (1.3%) | 57.6% | 0.0% (0.0%) | 13.1% |
| 25% | 0.9% (2.2%) | 52.6% | 0.5% (1.1%) | 49.4% |
| 50% | 1.2% (2.0%) | 61.8% | 0.9% (1.5%) | 56.0% |

Counting clears 0% in every run. G1 and G2 still pass. The low 13.1% at 10% deletion and
α = 0.05 is the sample-size effect: few apps have hole-dependent verdicts to calibrate on.

G3 status so far (witness oracle, `probes/witness.py`): the harness writes the call and the check;
the model only builds inputs, with a taint check on its statements, a control run with a
different source value, and a skip-call control. On 8 known cases it gives no false witnesses.
Of 123 data-carrying leak candidates, 6 flows FlowDroid misses were witnessed
(`DocumentsContract.buildDocumentUriUsingTree`, `ContentValues.put`, `Intent.createChooser`,
`DocumentsContract.getDocumentId`, `Contacts.getLookupUri`, `Intent.fillIn`). The source→sink
paths found for them so far look like in-app plumbing, not privacy leaks; they are re-extracted
after the rebuild.

## 13. G3 outcome: fallback (2026-09-28)

- **Witness oracle works; no privacy leak found.** With the harness writing the call and the check,
  a taint check on the model's statements, a control run and a skip-call control, it gives no
  false witnesses on 8 known cases. 6 witnessed flows FlowDroid misses complete 7 paths in 7 apps,
  all `Cursor.getString` → `ContentResolver.query/insert` plumbing inside the device.
- **Static no-flow checker does not help yet.** `extract/LibFacts.java` + `analysis/lib.dl` +
  `probes/oracle_static.py`: 0 disagreements with FlowDroid on its validation no-flow answers
  (13–26 atoms), and 400 receipt atoms proven absent. But 26 of those contradict the answer key,
  mostly checker errors on taint held inside objects created in one method and used in another
  (boxing in `Bundle.putDouble`, the cursor driver in `SQLiteDatabase.rawQuery`) and a stub base
  implementation (`InetAddress.getAddress`). Repricing them to 0.01 lowered certified clearance:
  36.9% → 36.1% (α = 0.1), 33.0% → 21.0% (α = 0.05). A sound checker needs a points-to heap model;
  StubDroid is the better route.
- **Lesson for the paper:** the calibration layer caught the checker's errors (held-out wrong
  clearances stayed ≤ 2%); a bad oracle costs power, not validity.

## 14. Next steps, in order

1. **Conformal layer:** split apps into calibration and test sets, conformal selection with the
   bound as the score, and report realized FDR on held-out apps. Needs more apps (target 100+), so
   fix scalability first (caveat 3).
2. **Labels for unmodeled facts:** a strong-LLM oracle plus human spot checks on cut facts only.
   Receipts are small, so this is cheap. Then include the 588 undetermined verdicts.
3. **Hole simulation on bundled libraries:** hide OkHttp/Gson/androidx bodies, derive truth from
   the unhidden analysis. That gives exact labels and tests generalization beyond memorized APIs.
4. **Isotonic or Learn-then-Test recalibration** of Choice prices inside the calibrated procedure,
   to push δ = 0.05 acceptance above 20%.
5. **Stronger LLM baseline** (e.g. a frontier model with logprobs) and a Praline comparison on the
   reachability fragment.
6. **Callback holes** as a second hole type.
