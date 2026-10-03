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

## 14. Scaled corpus: 143 apps, α = 0.05 now certifiable (2026-09-30)

Corpus: 216 downloaded apps; 147 build within the memory cap, 143 have hole-dependent verdicts.
New apps are built without keeping facts (`analysis/run_android.py` extracts each APK into a
temporary directory; `bench/scale.py` downloads in batches with a free-space guard). Many newer
apps with large Kotlin/Jetpack bundles exceed the 8–12 GB cap (38 of 76 in the last batch; one
measured app needed more than 12 GB): a cheaper heap model for bundled code is needed to go further.

Sound baseline B2 clears 70.6% of 42,093 leak-free sinks; the hard slice is 29.4% (12,379 clean
verdicts). App-level LTT, held-out, 200 splits:

| Target | Jev (flow rule stated): cleared / apps with a wrong clearance | B7 frequency prior | B4 counting |
| --- | --- | --- | --- |
| α = 0.1, ε = 0.1 | 36.9% / 1.3% | 11.3% / 2.6% | 0% |
| α = 0.05, ε = 0.1 | 30.6% / 0.6% | 6.3% / 0% | 0% |
| α = 0.05, ε = 0.05 | **30.6% / 0.6%** | 6.3% / 0% | 0% |

α = 0.05 at 95% confidence was not certifiable with 102 apps; with 143 it is. Total leak-free
sinks cleared: 81.4% (α = 0.1) and 79.6% (α = 0.05), against 70.6% for B2.

## 15. Scaled again: 332 apps, α = 0.02 now certifiable (2026-10-02)

**Build.** A restart-safe graph build on an 8-core / 62 GB server added 183 graphs from 367 new APKs
(184 failed in Soufflé, 50%, the same rate as the last batch; 14 h 7 min), for 332 graphs in total.
The survivors are larger than before (6.1 MB per graph against 0.9 MB), so evaluating them is slow: the
Jev-priced run took 6 h 57 min, `uniform` 3 h 25 min and `freq` 4 h 41 min. The slowest three or four
apps cost 1.5 to 3 h per run.

**Pricing and answer key.** 1,275 framework methods (3,892 candidate flows) on the new graphs were not in
the old hole file (`probes/extend_holes_fw.py`). All were priced with Jev (same model version as every
earlier price, `jev-1.13-20260917`, object convention stated) and the 865 that FlowDroid does not model
were labeled by Sonnet 5 ($0.70). Old records and labels are unchanged.

**Result.** 324 of the 332 apps have hole-dependent verdicts: 84,793 sinks, of which 28,335 are
clean, 56,418 real flows and 40 undetermined. App-level LTT, held-out, 200 splits, ε = 0.1:

| Pricer | Cleared, α = 0.1 | Cleared, α = 0.05 | Held-out apps with a wrong clearance (α = 0.1 / 0.05) |
| --- | --- | --- | --- |
| B4 counting guesses (uniform price) | 0% | 0% | 0% |
| B7 frequency prior | 9.2% | 6.6% | 4.9% / 0.8% |
| Jev, flow rule stated | **40.0%** | **40.0%** | 1.0% / 1.0% |

Jev also certifies α = 0.02 (ε = 0.1): 33.4% cleared, 0.3% of held-out apps with a wrong clearance;
α = 0.05 at ε = 0.05 gives the same 40.0% / 1.0% as at ε = 0.1. Counting clears nothing, and clearing
receipts of size 1 is already unsafe: a wrong clearance in 302 of 324 apps (93%).
Against 143 apps (36.9% / 30.6%, §14) the clearance is higher and the guarantee still holds.

**The threshold sits on a cliff.** Jev chooses δ = 0.3 in all 200 splits for α ≥ 0.05; apps with a wrong
clearance jump from 3 of 324 at δ = 0.3 to 135 of 324 at δ = 0.5. The three apps at δ = 0.3 have three
different causes, not one widely bundled fact: `Boolean.valueOf(boolean)` arg0→ret (FlowDroid summary,
priced 0.29, a genuine Jev underestimate), `BitmapFactory.decodeStream` arg0→arg2 (Sonnet label, priced
0.13, nine sinks in one app) and `View.setVisibility(int)` arg0→this (Sonnet label, priced 0.15). Two of
the three depend on a silver label that is arguable under the object convention, so they may be label
noise and not Jev errors; the planned hand audit of cut facts should settle them.

**Caveats.** (1) The new apps are larger and half the new ones fail to build, so the step from 143 to 324
apps is not a clean replication. (2) The answer key is still FlowDroid plus Claude labels. (3) The
share of all leak-free sinks cleared (B2 plus the hard slice) was not recomputed for this corpus.
(4) The deletion benchmark K1 was not rerun. (5) Bundled libraries shared across apps are not
deduplicated. (6) The three or four largest apps were included in every run; none timed out.

Results: `data/scale332/android_{choice-obj,uniform,freq}.jsonl` (the 143-app files in `data/` are unchanged).

## 16. Audit of the answer key behind accepted receipts (2026-10-02)

**Population.** The 11,324 accepted sinks (bound ≤ 0.3, determined truth) rest on only 446 distinct library
facts (`analysis/audit_sheet.py`; the top 50 carry 81% of fact-uses). The key labels them: 143 FlowDroid summary,
52 FlowDroid omission, 246 Sonnet silver, 5 unlabeled. A reviewer answered all 446 blind (no key, no price): "if
X holds a secret before the call, does Y hold it or anything built from it afterwards?"

**First pass (instruction: the object-granularity rule, loosely stated).** 303 no, 95 yes, 48 unsure; agreement
with the key on decided rows 78.1% (summary 88%, omission 76%, silver 72%). It was almost one-sided: key no and
reviewer yes in 85 rows. Taken at face value, 12.1% of accepted sinks at δ ≤ 0.3 (72% of apps) would have a
fact in the receipt that the reviewer says exists, which would have pulled the safe threshold down to δ ≈ 0.05–0.1.
The notes show why: many yes answers counted things that could happen in unusual cases (custom subclasses,
callbacks, older OS versions) or influence on a result (an index picks an element, a delay is stored).

**Strict recheck of the 95 yes rows.** The reviewer was given a precise rule (`AUDIT_RECHECK.md`): ordinary
documented behavior only, no custom overrides or callbacks, no OS-version details, no caches or bookkeeping that keep
nothing from X, influence is not a flow, and a yes needs a named mechanism and a reason code. Result: 86 of the 95
flipped to no (codes: incidental 40, control 20, pick 15, hypothetical 10, none 1) and 9 stay yes (copy 2, store 3,
read 4). Combined with the first pass: 389 no, 9 yes, 48 unsure; **agreement with the key 97.7%** (384 of 393
decided: summary 132/133, omission 39/42, silver 213/218).

| Accepted sinks whose receipt holds a fact answered yes | strict | first pass |
| --- | --- | --- |
| δ ≤ 0.05 | 0 of 1,563 (0 apps) | 19 (1.2%), 8 of 198 apps |
| δ ≤ 0.10 | 3 (0.1%), 2 of 296 apps | 101 (2.4%), 49 apps |
| δ ≤ 0.20 | 3 (0.0%), 2 of 316 apps | 731 (8.0%), 185 apps |
| δ ≤ 0.30 | 31 (0.3%), 11 of 316 apps | 1,370 (12.1%), 229 apps |

These are upper bounds: a receipt fact that exists does not by itself make the sink a real flow. Under the strict
rule the audit supports the certified threshold: even if all 11 apps were genuinely wrong, 3.5% of apps is below α = 0.05.

**What the strict audit says about the key.** (a) All three wrong clearances of §15 are confirmed as real flows
(`Boolean.valueOf`, `BitmapFactory.decodeStream` into Options, `View.setVisibility`), so they are not label noise.
(b) Five facts the key calls absent are still yes (`View.setImportantForAccessibility`, `Bundle.isEmpty`,
`BitmapFactory.decodeByteArray` into Options, `Cursor.getColumnIndex`, `File.createTempFile`): candidate key errors, 13
accepted sinks in at most 8 apps. (c) Four facts the key calls present are no under the strict rule, three of them name
lookups the reviewer treats as picks (`Charset.forName`, `Class.forName`, `Enum.valueOf`): there the key is more cautious
than the rule, which can only lower the number of wrong clearances.

**Caveats (these must be stated with the result).** (1) The strict instruction was written after seeing that the
first pass disagreed with the key by 78%, so it was not fixed in advance; the 97.7% is agreement under a rule chosen
with that knowledge, and the 78% under the looser reading is equally real. The guarantee is about one definition of
"flow", and the paper has to state it precisely. (2) The 48 unsure rows were never resolved (336 accepted sinks, 3%,
depend on one) and the recheck used no unsure at all, although it was encouraged. (3) Only the 303 first-pass no
answers were not rechecked. (4) The identity of the reviewer (human or model) and whether it was independent of the
labels' model must be stated before this is called an audit; if it was a model, call it a second-model audit. (5) The
audit covers facts in receipts at δ = 0.3 only, and checks them, it does not re-derive truth for rejected verdicts.

**Follow-up (2026-10-03): the 48 unsure rows and an independent sample.** Under the same strict rule 30 of the 48
unsure rows became no and 18 stay unsure (all 48 had the key label no). A 60-row sample drawn from the 446 (all 9 strict
yes rows, the 4 rows where the key says yes and the audit says no, and 47 random others, shuffled, without any earlier
answers shown) was answered again; the `answered_by` column of both files says "AI-assisted" on every row. It agrees
with the strict reviewer on all 60 rows (51 no, 9 yes) and with the key on 50 of 59 labeled rows (84.7%; the 9
disagreements are the 5 candidate key errors and the 4 key-yes rows already listed, which were forced into the sample).
Final audited answers: 419 no, 9 yes, 18 unsure. Accepted sinks by the audit status of their receipt:

| Threshold | Accepted sinks | All facts no | Some fact unsure | Some fact yes (upper bound on wrong clearances) |
| --- | --- | --- | --- | --- |
| δ ≤ 0.05 | 1,563 | 100.0% | 0 | 0 |
| δ ≤ 0.10 | 4,287 | 99.9% | 0 | 3 (0.1%), 2 of 296 apps |
| δ ≤ 0.20 | 9,107 | 97.7% | 205 (2.3%) | 3 (0.0%), 2 of 316 apps |
| δ ≤ 0.30 | 11,324 | **97.6%** | 246 (2.2%) | 31 (0.3%), 11 of 316 apps |

The agreement of the two later passes with each other shows that the written rule can be applied consistently; it
does not show that either pass is right, since both are AI-assisted and used the same rule. The reviewer of the first
two passes is still unnamed. For the paper this is a second-model audit; the human check the plan calls for (a person
reading the source for a sample) is still open.

**Working definition of a flow (2026-10-03, drafted by the reviewer; to be confirmed by the authors).** We evaluate
documented API-level data transfer under ordinary executions with standard arguments. A flow occurs when source data, a
computed representation of it, or a reference to it reaches the target through copying, storage or readout, including
documented properties. Mere selection or control, incidental bookkeeping, and custom callback or override behavior are
excluded. Cases that cannot be determined from the API contract remain unknown. A negative label therefore denotes no
transfer within this scope, not absence of every possible information flow. FlowDroid has optional implicit-flow
tracking (its default, used here, is explicit flows only), so the paper must state this scope as a choice and not claim
that no tool supports implicit flows. The 60-row sample was built to contain every disputed row, so its agreement
figures describe those rows and are not an estimate of the error rate of all 446.

Files: `data/audit/audit_facts.csv` (first pass), `data/audit/audit_recheck.csv` (strict), `audit_unsure.csv`,
`audit_human_sample.csv`, key in `data/audit_private/audit_key.csv`; instructions `AUDIT_TASK.md` and `AUDIT_RECHECK.md`.

## 17. Sound baseline on 324 apps, bound-combination ablation, faster evaluation (2026-10-02)

**B2 on the full corpus.** Over the 324 apps with hole-dependent verdicts there are 169,700 sink calls with a
non-constant argument; 96,945 are reachable with every hole on. B2 clears the other 72,755: **72.0% of the 101,090
leak-free sinks**; the hard slice is the remaining 28.0% (28,335 clean sinks). Adding Jev at the certified
threshold: total cleared 73.5% (δ ≤ 0.05), 76.2% (0.10), 81.0% (0.20), **83.2% (0.30)**, against 72.0% for B2
(§14 on 143 apps: 70.6% and 79.6%). The sink-call counts of the 104 older graphs come from their kept facts
(`data/sink_calls_old.json`), the other 228 from the graphs.

**A1: how receipt prices are combined** (`analysis/ablation_a1.py`, 324 apps, ε = 0.1, 200 splits, same cut):

| Bound | α = 0.05: chosen δ | held-out apps with a wrong clearance | clean hard-slice verdicts cleared | uncalibrated at δ = α: apps wrong / cleared |
| --- | --- | --- | --- | --- |
| sum over cut edges (ours) | 0.3 | 1.0% | 40.0% | 0 of 324 / 5.5% |
| sum over distinct facts | 0.3 | 1.0% | **43.0%** | 0 of 324 / 6.0% |
| largest single price | 0.2 | 0.6% | **46.8%** | 0 of 324 / 6.3% |
| independence product | 0.3 (0.2 in 16 splits) | 1.9% | 45.3% | 0 of 324 / 4.9% |

Three consequences. (1) Validity comes from the program-level calibration, not from the union bound: every
combination meets α once calibrated. The plan expected the independence product to break the α target; it does not,
neither calibrated nor at the nominal threshold (no wrong clearance in any app at δ = α), because the prices are
conservative at the low end. The paper must not claim that the sum is needed for validity. (2) The sum is not the
most powerful score: the largest single price clears 46.8% against 40.0%. What the sum buys is a reading that holds
without calibration if the prices are calibrated, and receipts a person can add up. (3) Counting each fact once
(a fact used at several call sites) is valid and gives +3 points for free; it should be the default bound.

**Evaluation speed.** Evaluating the 332 graphs took 3.5 to 7 hours per pricing, dominated by the heaviest apps
(e.g. 18.2M code edges, 10.9 s per sink, 84% in `maximum_flow`). Code edges have infinite capacity, so a finite cut
never separates a strongly connected group of them: contracting each group once per app leaves bounds and cuts
unchanged and makes max-flow about 25x faster on those apps (0.35 s per sink). The new `evaluate.py` returns identical
records to the old one on real graphs in Jev, uniform and deletion modes and on the first 25 sinks of two heavy apps;
the full-scale regression (332 apps) is the first job of the overnight queue.

**B6 (feature classifier).** Logistic regression on signature features (name tokens, package, types, flow kind),
trained on FlowDroid-modeled atoms and cross-fitted by method, ranks held-out modeled atoms better than Jev
(AUROC 0.98 against 0.875 for Jev's object-convention prices and 0.81 for B7 on the same 13,915 atoms). It learns
FlowDroid's own conventions from sibling methods, so it is expected to be strong on the deletion benchmark (K1) and
weaker on methods FlowDroid never modeled; both keys must be reported.

**B6 against Jev on both keys** (324 apps, program-level LTT, ε = 0.1, 200 splits, held-out).

Main key (FlowDroid plus Sonnet labels for unmodeled methods; hard slice 28,335 clean verdicts). B6 needs a finer
threshold grid than the default (its prices are low: 15 of 324 apps already have a wrong clearance at δ = 0.01), so it
was given δ ∈ {0.001 … 0.02}; with the default grid it cannot be certified at α = 0.05.

| Pricer | Cleared, α = 0.10 | Cleared, α = 0.05 | Apps with a wrong clearance (0.10 / 0.05) |
| --- | --- | --- | --- |
| counting (uniform) | 0% | 0% | 0% |
| B7 frequency prior | 9.2% | 6.6% | 4.9% / 0.8% |
| B6 feature classifier (finer grid) | 33.2% | 22.0% | 5.4% / 0.7% |
| Jev | **40.0%** | **40.0%** | 1.0% / 1.0% |

Deletion benchmark K1 (truth = FlowDroid's models, no LLM in the key; 5 seeds, mean; deleted methods are also
removed from B6's training data; `analysis/k1_summary.py`):

| Deleted | Pricer | Cleared α = 0.1 | Wrong clearances α = 0.1 (worst seed) | Cleared α = 0.05 | Wrong clearances α = 0.05 (worst seed) |
| --- | --- | --- | --- | --- | --- |
| 10% | B6 | **87.8%** | 2.4% (4.0%) | **85.9%** | 0.7% (1.9%) |
| 10% | Jev | 62.9% | 1.0% (4.3%) | 60.1% | 0.2% (0.8%) |
| 25% | B6 | **88.1%** | 2.8% (5.5%) | **87.5%** | 0.2% (0.7%) |
| 25% | Jev | 59.5% | 0.9% (3.4%) | 56.8% | 0.4% (0.9%) |
| 50% | B6 | **82.8%** | 2.3% (6.0%) | **81.5%** | 0.3% (1.2%) |
| 50% | Jev | 63.7% | 0.6% (0.7%) | 63.7% | 0.6% (0.7%) |
| any | counting | 0.0% | 0.0% | 0.0% | 0.0% |

The ranking flips with the key. On K1 the classifier clears 20 to 30 points more than Jev, within the risk target
in every run (worst seed 6.0% against 10%); on the main key Jev clears 7 to 18 points more. This is expected: K1
holes are methods FlowDroid chose to model, and B6 is trained on FlowDroid's labels of sibling methods (same name,
other class), so K1 is close to in-distribution for it. The real holes are methods FlowDroid never modeled, which is
what the main key contains, and there B6 has no siblings to copy. Consequences for the paper: do not claim that Jev
beats simple pricers in general; the claims that hold are (1) receipts are only certifiable with calibrated prices
(counting 0%, frequency prior 6 to 9%, classifier and Jev 20 to 90%), (2) which pricer is best depends on whether the
holes resemble what FlowDroid already models, and (3) Jev needs no labeled corpus. Report both keys side by side.
The K2 key (StubDroid on the real code) would be a third, independent view.

## 18. Whole-class deletion, IRIS-style and Praline-style baselines (2026-10-03)

**Why a class-level deletion benchmark.** The method-level K1 deletes single methods, so a deleted method almost
always keeps modeled siblings (same name, other class) that B6 learns from. 86% of the real unmodeled methods that
matter (12,274 methods with candidate flows) belong to classes with no modeled method at all. In the class-level run
(`k1c-`), whole classes are deleted, and B6 is also cross-fitted and trained without them. With classes held out, B6's
ranking quality on modeled atoms falls from 0.980 to 0.942 AUROC (Jev 0.875), and its low-end error rises: 2.4% of
atoms it prices below 0.05 are real flows, against 0.1% for Jev.

Class-level deletion, 3 seeds, mean (held-out apps with a wrong clearance in the worst seed in brackets; hard-slice
clean / real verdicts 681 / 1,201 at 10%, 5,087 / 8,773 at 25%, 11,650 / 20,153 at 50%):

| Classes deleted | Pricer | Cleared α = 0.10 | Wrong clearances α = 0.10 | Cleared α = 0.05 | Wrong clearances α = 0.05 |
| --- | --- | --- | --- | --- | --- |
| 10% | B6 (class folds) | 99.1% | 3.7% (4.2%) | 87.0% | 1.5% (1.9%) |
| 10% | B6 + Jev price | 98.9% | 3.3% (4.5%) | 98.8% | 0.7% (1.4%) |
| 10% | Jev | 62.6% | 0.4% (1.3%) | 62.2% | 0.3% (1.0%) |
| 25% | B6 (class folds) | 81.8% | 3.1% (4.3%) | 71.4% | 1.6% (2.1%) |
| 25% | B6 + Jev price | **89.7%** | 2.8% (3.3%) | **86.3%** | 1.5% (2.0%) |
| 25% | Jev | 60.8% | 1.9% (3.2%) | 52.2% | 0.8% (1.3%) |
| 50% | B6 (class folds) | 39.7% | 0.3% (0.9%) | 39.7% | 0.3% (0.9%) |
| 50% | B6 + Jev price | **79.5%** | 2.1% (5.6%) | **60.7%** | 0.3% (0.7%) |
| 50% | Jev | 56.1% | 1.4% (1.9%) | 53.8% | 1.3% (1.6%) |
| any | counting | 0.0% | 0.0% | 0.0% | 0.0% |

B6's lead disappears as more classes are removed (it has less to learn from: 39.7% against Jev's 56.1% at 50%), and
the hybrid that adds Jev's price as a feature is the strongest in the heavier settings. The real hole population is
more extreme than 50% of classes (FlowDroid models roughly a third of the methods); runs at 75% and 90% follow.

**IRIS-style baseline (B3): the LLM's yes/no taken as fact.** Sonnet 5 (same model and prompt as the silver key)
labeled all 5,556 FlowDroid-modeled methods ($4.10); price 1.0 for yes, 0.0 for no; a verdict is cleared when no path
exists using only the yes answers. It has one operating point and no risk knob. Over the 18 deletion runs
(`analysis/b3_summary.py`):

| Deletion | Seeds | Clean verdicts cleared | Apps with a wrong clearance (mean / worst seed) |
| --- | --- | --- | --- |
| methods 10% | 3 | 80.8% | 5.0% / 7.7% |
| methods 25% | 3 | 88.2% | 6.3% / 6.4% |
| methods 50% | 3 | 90.5% | 6.3% / 7.0% |
| classes 10% | 3 | 86.3% | 0.0% / 0.0% |
| classes 25% | 3 | 79.9% | 0.8% / 2.5% |
| classes 50% | 3 | 88.0% | 2.7% / 6.0% |

On these keys the baseline is strong: it clears about 86% of the clean hard-slice verdicts with 3.5% of apps holding a
wrong clearance on average, above the 5% target in 9 of 18 runs, never above 10%. It is lumpy: the same 19 apps and
about 35 sinks recur in many runs (one wrong answer about a fact bundled in many apps), so its error is either near
zero or about 6 to 8% of apps, depending on whether that fact was deleted. That correlated error across apps is what
the per-app calibration is built for, and a risk level cannot be chosen or certified for B3. Caveats: (1) the deleted
methods are well-known APIs that the model probably memorized, so these keys favor it; (2) on the main key it is
circular (its answers are the key's labels for unmodeled methods) and that run was stopped (27 apps, excluded);
(3) Sonnet agrees with FlowDroid on 94% of atoms (§8), so K1 truth and B3 share information.

**Praline-style comparison (no Praline code is available; this is its optimum, not its tool).** Praline (OOPSLA 2025,
"Probabilistic Inference for Datalog with Correlated Inputs") bounds the probability of an output fact given input
marginals and partly known correlations, by constrained optimization with an SMT-based refinement. With only the
marginal p_e of each fact known and arbitrary correlation allowed, the largest possible probability that the sink is
derivable is min(1, min-cut with capacities p_e): any path needs an edge of each cut (union bound), and a maximum
flow of value F ≤ 1 decomposes into paths f_k; the world "exactly the edges of path k" has probability f_k, which
meets every marginal (conservation) and reaches the sink with probability ≥ F. Numerical check
(`analysis/praline_check.py`): the exact optimum, solved as a linear program over all 2^m worlds, equals
min(1, max-flow) on 190 random graphs with 5 to 11 edges (largest difference 2e-15). The mean gap to the
exact probability under independence was 0.08 to 0.17, so an independence-based bound understates the risk
(consistent with the A1 ablation, where the independence product needed calibration to meet the target). The
world-enumerating LP takes 0.04 s at 5 edges and 0.27 s at 10, against 0.01 s for max-flow. Limits: the claim holds
for the information we have (marginals only); Praline can exploit known correlations that we do not have, and its own
algorithm avoids enumerating worlds, so the comparison is on the optimum and not on its speed. The honest conclusion is
that on the reachability fragment the cut is not a weaker bound than Praline's; the contribution is the program-level
calibration, the receipts and the pricing.

## 19. Next steps, in order

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
