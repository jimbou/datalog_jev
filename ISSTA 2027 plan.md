# Soundiness with Receipts — ISSTA 2027 plan

Sep 27, 2026 · @Dimitrios Stamatios Bouras

Target ISSTA 2027, full paper due Jan 11, 2027: 15 weeks, about 420 person-hours, and under $700 in API calls and cloud compute.

## Timeline

&#91;embedded content: work plan · 15 weeks, 4 gates\]

Each gate is a go/no-go check with a named fallback (see Risks and fallbacks). If ISSTA slips, the next CCF-A slot is OOPSLA 2027 round 2 (Apr 7, 2027), which fits a version with the formal treatment and a second hole type.

## Claims and research questions

The paper makes three claims: priced receipts give a certified per-app false-clearance rate for an unsound taint analysis; they clear far more leak-free verdicts than a sound over-approximation at the same risk; and receipts tell you which holes to close, which finds leaks the analysis missed.

| RQ | Question | Metric | Bar to clear |
| --- | --- | --- | --- |
| RQ1 | Is the pricer calibrated, including on libraries it knows less well? | AUROC, ECE, Brier, reliability diagram, per library family | AUROC ≥ 0.90 on Android, ECE ≤ 0.05; report the drop on third-party libraries |
| RQ2 | Does the guarantee hold? | Share of held-out apps with any wrong clearance, at α = 5 / 10 / 20%, over 200 random splits | Observed ≤ α on the deletion benchmark and on both answer keys |
| RQ3 | Is it useful? | Coverage: share of leak-free verdicts cleared at α | Beats the sound baseline (B2) and the unweighted cut (B4) |
| RQ4 | Does closing holes pay off? | Coverage vs number of holes discharged; confirmed missed leaks | +15 points coverage by 500 discharges, or ≥ 1 confirmed leak FlowDroid missed |
| RQ5 | What does it cost? | Time, peak memory, $ per app | Pricing and cuts add < 10% to analysis time |
| RQ6 | Does it transfer? | RQ2 and RQ3 when calibrating on F-Droid and testing on Play Store apps | Report whether the guarantee holds; no bar |
| RQ7 | Does it carry over to a second kind of hole? | RQ2 and RQ3 on framework-callback holes (see Second hole type) | Observed ≤ α on the callback key; report coverage, no coverage bar |

RQ6 is the first thing to cut if time runs short, RQ7 the second.

## Benchmarks

The core set grows from 103 to at least 300 usable F-Droid apps, which is what a 5% guarantee needs with half the apps held out. Everything else is either derived from that set or small.

| Benchmark | Size | Used for | Effort |
| --- | --- | --- | --- |
| F-Droid apps (have 130) | Download 400, aim for ≥ 300 that run | Calibration and test for RQ1–RQ5 | 2 days; reuse the existing scripts. Deduplicate bundled libraries (same package and version analysed once, shared across apps) so apps sharing a library do not count as independent evidence |
| Deletion benchmark (derived) | 100 F-Droid apps × 3 deletion rates (10, 25, 50%) × 5 seeds | Non-LLM ground truth for RQ2 | Post-processing only, if summary edges are tagged (see Ground truth) |
| JDK flow questions (have) | 3,971 questions | RQ1 on well-known code | Done |
| Third-party library questions (new) | \~1,500 questions from OkHttp, Gson, Guava, Apache Commons, Play Services | RQ1 and RQ6 on code the pricer knows less well | 3 days; labels from StubDroid plus witness tests |
| [TaintBench](https://ris.uni-paderborn.de/record/27045) | Real malware apps with documented flows | Do receipts flag the documented leaks that pass through library code? | 2 days |
| AndroZoo Play Store sample | 100 apps, same size range as F-Droid | RQ6, test only | Apply for AndroZoo access this week |

OWASP stays in the paper as one paragraph: its verdicts never depend on library behaviour, so every receipt is empty. DroidBench is a sanity check only.

## Ground truth

The main RQ2 result must rest on a key with no LLM in it; the current FlowDroid-plus-Sonnet key becomes one of three.

| Key | How it is built | LLM in it? | Role |
| --- | --- | --- | --- |
| K1: model deletion | Run with FlowDroid's full summaries as truth. Delete 10/25/50% of the summaries, turn them into priced holes, and check whether the receipts catch the verdicts that became wrong. | No | Headline RQ2 result |
| K2: code-derived | StubDroid summaries generated from the real Android implementation (android-all jar) for every hole on a source–sink path | No | Second key for RQ2 and RQ3 |
| K3: current key | FlowDroid summaries plus Sonnet 5 answers for unmodeled methods | Yes | Kept for comparison (ablation A8) |
| Receipt audit | 400 facts drawn from receipts, at least 200 from receipts of verdicts the method cleared; two raters, Cohen's kappa; each also run through a witness test | No | Checks the facts the guarantee actually rests on; measures the error rate of K2 and K3 |

One engineering change makes K1 nearly free: tag every summary-derived edge in the flow graph with the method it came from. Deleting a model then means relabelling those edges as holes and recomputing cuts, with no new analysis run.

### Independent validation of receipts

The guarantee rests on the facts inside receipts, so those facts get checked without any LLM deciding a label. This answers the reviewer question "is the answer key just one AI grading another?"

- **Sample.** 200 facts from receipts of cleared verdicts, stratified by price (below 0.02, 0.02–0.05, 0.05–0.2), plus 200 from receipts of uncleared verdicts as a control.
- **Hand audit.** Two raters read the real implementation (AOSP or JDK source) of each method and label flow / no flow under the stated flow rule; disagreements are discussed and settled; Cohen's kappa is reported.
- **Dynamic check.** The same facts go through oracle 2 of the closing loop: a witness test runs the real method with a marker value. Sonnet writes the test, but only running it decides the label. A passing test inside a cleared verdict's receipt is a direct miss and is reported as one.
- **Report.** Observed flow rate per price band against the mean price in that band, and the number of cleared verdicts whose receipt contains an audited or witnessed flow.

A test can only prove that a flow exists, never that it does not, so the hand audit carries the "no flow" side and the tests catch audit mistakes on the "flow" side.

## Models

Jev stays the main pricer. An open-weight model is added so the paper has a fully reproducible configuration if Jev cannot be released.

| Role | Model | Calls | Why this one |
| --- | --- | --- | --- |
| Main pricer | Jev | \~126k questions (40k on-path hole questions × 3 prompt variants, plus JDK and third-party sets) | Calibrated probabilities at $0.00002 a question |
| Reproducible pricer | Qwen3-8B (or a similar open 7–8B model), yes/no token probabilities | Same 40k questions | Open weights; about 10 GPU-hours |
| Answer key for newly seen methods | Claude Sonnet 5 | \~6k methods | Already used for K3; 94% agreement with FlowDroid |
| Stated-confidence baseline | Claude Sonnet 5 | \~10k on-path methods, one call each covering all flows | The obvious "just ask a strong model" baseline |
| Self-consistency baseline | Claude Sonnet 5, 5 samples | 2k-method stratified sample, RQ1 only | Tests sampling-based confidence without paying for every hole |
| Witness-test writer | Claude Sonnet 5 | \~1,500 holes × \~2.5 attempts | Writes JVM/Robolectric tests that show a flow exists |
| Feature classifier | Logistic regression on method-signature features | Local | The cheap non-LLM pricer (B6) |

Only holes on at least one source–sink path get priced. That keeps question counts in the tens of thousands, not the 350,000 call sites.

## Baselines

B2 is the one that can sink the paper, so it runs first, at gate G1 (Oct 11).

**G3 (Sep 28): fallback taken.** Leak criterion met only formally: witness tests (running the real library code, two controls, no false witnesses on 8 known cases) confirmed 6 data-carrying flows FlowDroid's models miss, and they complete 7 source→sink paths in 7 apps, but all are database-to-database plumbing (`Cursor.getString` → `ContentResolver.query/insert`), not privacy leaks. Clearance criterion not met: a home-built static no-flow checker (analysis/lib.dl, 0 errors against FlowDroid on 13–26 validation answers) proved 400 receipt atoms absent, but 26 of its answers contradict the answer key, mostly its own errors on taint held inside objects created in one method and used in another; repricing them lowered certified clearance (36.9% → 36.1% at α = 0.1, 33.0% → 21.0% at α = 0.05). Decision: the paper leans on RQ2/RQ3; closing becomes a short section. If revisited, use StubDroid on the real Android code as oracle 1 instead of the home-built checker.

**Rerun with FlowDroid's default source/sink list (Sep 27, evening): G1 and G2 still pass.** The earlier runs had used FlowDroid's disabled inter-component sources/sinks too. Corrected: B2 clears 70.8% of leak-free sinks; on the 29.1% hard slice Jev clears 36.9% (α = 0.1) and 33.0% (α = 0.05), B7 7.5% / 6.2%, B4 0%; held-out wrong clearances about 1% of apps. K1: wrong clearances 0.4–1.2% (α = 0.1), cleared 53–62%. The numbers below are superseded by these (FINDINGS.md §12).

**G2 result (Sep 27, early): passed on K1.** Deletion benchmark, 103 apps, 10/25/50% of FlowDroid models deleted, 5 seeds each: held-out apps with a wrong clearance 0.9–1.5% at α = 0.1 (worst seed 2.6%) and 0.4–0.7% at α = 0.05; Jev clears 76–87% (α = 0.1) and 69–81% (α = 0.05) of hard-slice leak-free verdicts; counting guesses clears 0%. Details in FINDINGS.md §11.

**G1 result (Sep 27, 103 apps): passed, with a reframing.** B2 clears 77.9% of leak-free sinks on its own; our 41% is over the remaining hard slice (22.0% of leak-free sinks), for 86.9% in total. On that slice, certified at the app level: B2 0%, B4 0% (clearing even size-1 receipts gives a wrong clearance in 100 of 103 apps), B7 9.0%, Jev 41.3% (α = 0.1) and 34.8% (α = 0.05). Lead the paper with the hard slice and state the 78% up front.

| ID | Baseline | What it shows | Cost |
| --- | --- | --- | --- |
| B1 | Optimistic: every hole means "no flow" (FlowDroid today) | Clears everything; its wrong-clearance rate is the motivation | Free |
| B2 | Sound over-approximation: every hole means "flow" | Clears only verdicts with empty receipts, at zero risk. If this is close to 41%, pricing adds little. | Free |
| B3 | Trusted LLM specs (IRIS-style): Sonnet 5 says yes/no per flow, taken as fact | Coverage and error with no guarantee | Reuses the K3 calls |
| B4 | Unweighted cut (Bastani et al. 2015 style): clear if the receipt has ≤ k guesses, k tuned on calibration apps. This is also the uniform-price baseline: one flat price for every guess gives the same clearances. | What pricing adds over counting | Free |
| B5 | Other pricers under the same cut and calibration: stated confidence, self-consistency, open-weight token probabilities | That the result is not Jev-specific | See Models |
| B6 | Feature classifier on signatures (get/set/append/to\* prefixes, return and parameter types, package) | A cheap non-LLM pricer | Local |
| B7 | Frequency prior: share of modeled methods in the same package and flow kind that do have the flow | The simplest possible prior | Free |

For RQ4, compare closing orders: random, popularity only, lowest p first, highest uncertainty first, and expected value (Selection rule, below).

## Ablations

Store each app's flow graph with hole and summary tags once; after that, every ablation except A6 is post-processing and costs minutes.

| ID | What changes | Variants | New analysis run? |
| --- | --- | --- | --- |
| A1 | How guesses combine | Min-cut + sum (ours); sum over every hole on any path; largest single hole; product assuming independence | No |
| A2 | Calibration unit | None; per verdict; per app (ours); per cluster of apps sharing bundled libraries | No |
| A3 | Question format | Yes/no; pick-an-answer; pick-an-answer with the flow rule (already run) | No, re-pricing only |
| A4 | Pricer | Jev vs B5–B7 | No, re-pricing only |
| A5 | Hole identity | Per method vs per method × call site | No, merge or split hole ids |
| A6 | Analysis precision | Current vs type-aware | Yes, about 100 apps that fit both |
| A7 | Closing order | Random; popularity only; lowest p first; highest uncertainty; expected value (ours) | No, replays discharge results |
| A8 | Answer key | K1; K2; K3; audit subset | No |

A1 with the independence product should break the α target. Show that it does: it is the reason for the union bound.

## Closing the holes

Receipts become a to-do list: with a budget of 1,500 holes, verify the guesses that the most uncleared verdicts depend on, then recompute the cuts.

1. **Pick.** Rank holes by expected value per check (Selection rule, below), not by popularity. Take the top 50, discharge them, recompute cuts, repeat.
2. **Oracle 1, static.** Run FlowDroid/StubDroid on the method's real body (android-all jar or the library jar) with a bounded call depth. Answers: no flow, flow, or unknown (timeout, native code, reflection).
3. **Oracle 2, dynamic.** Sonnet 5 writes a test that passes a marker string into the method and checks the return value and object fields for it: plain JUnit for java.\* and third-party jars, Robolectric for Android framework classes. A passing test proves the flow exists.

| Result | What happens to the hole | Effect on verdicts |
| --- | --- | --- |
| No flow (oracle 1, no unknowns) | Price drops to a small ε, not 0, because the bounded analysis is not a proof | More verdicts cleared |
| Flow witnessed (oracle 2) | Edge becomes certain | If it completes a source–sink path: a leak report with a runnable witness, then confirmed by hand in the app's source |
| Unresolved | Keeps its price | None |

Symbolic execution is left out to keep the scope reasonable. When scoring RQ4, do not use K2 as truth, since oracle 1 is built on the same tool; use witnesses and the audit.

### Selection rule

Rank holes by the expected change a check buys, using Jev's price as the probability of each outcome. Popularity alone wastes checks: a hole at p = 0.97 in 5,000 receipts will almost surely come back "flow" and clears nothing, while a hole at p = 0.02 barely moves any bound.

Only verdicts not yet cleared (bound B\_v > τ) count.

| Term | Definition |
| --- | --- |
| Clearing gain | Verdicts that drop to τ or below if h is proven no-flow. Quick test: h in v's receipt and B\_v − p\_h + ε ≤ τ; recompute the cut exactly for top candidates. |
| Leak gain | Verdicts whose remaining min cut is ≤ δ when p\_h = 1, i.e. a source–sink path is nearly open. A witness for h turns them into leak candidates. |
| Resolvable | Chance the checkers settle h at all; low for native code and reflection |
| Cost | Expected checker cost for h (tokens, CPU) |

```latex
\mathrm{score}(h) = \frac{\big[(1 - p_h)\,\mathrm{clear}(h) + p_h\,\mu\,\mathrm{leak}(h)\big]\cdot \mathrm{resolvable}(h)}{\mathrm{cost}(h)}
```

μ sets how much a found leak is worth relative to one cleared verdict. Example: a getter at p = 0.3 in 400 receipts with bounds near 0.35 and τ = 0.1 scores about 280 expected clears and outranks `append`.

1. Build the hole-to-uncleared-verdict index from the receipts.
2. Score all holes; check the top 50.
3. Update prices: no flow → ε (the checker's audited error rate); witnessed → 1; unresolved → unchanged.
4. Recompute cuts only for verdicts whose receipts contain a checked hole.
5. Stop when verdicts cleared per check falls below a floor.

Details to get right:

- **AND verdicts.** A verdict needing two holes gives each hole zero solo gain. Add pair gains for the top \~200 co-occurring holes; report greedy vs the exact ILP on a sample.
- **Apps vs verdicts.** The guarantee is per app. Report gain in both units and fix the objective before running.
- **Pricer disagreement.** Holes where Jev and Sonnet or the open-weight model disagree get a bonus; they are the likeliest systematic errors.
- **Validity.** Rank and check on the ledger split only, freeze the checked set, then calibrate.

## Second hole type: framework callbacks

The analysis already skips a second kind of behaviour: the framework calling back into app code, such as lifecycle methods (`onCreate`) and listeners (`onClick`, `onLocationChanged`). Today those dispatches are dropped, which is the same unsound shortcut as dropping library flows. Pricing them shows the method is not specific to library summaries (RQ7).

- **Candidates.** For each framework call that registers a callback object (`setOnClickListener`, `requestLocationUpdates`, `registerReceiver`, …), an edge into each app override of the matching callback method, carrying the framework's arguments (for example the `Location` object) into its parameters.
- **Pricing.** Jev answers whether the framework invokes that callback with that data, in the same pick-an-answer format with the rule stated.
- **Answer key without an LLM.** FlowDroid's `AndroidCallbacks.txt` and its lifecycle model decide which callbacks can fire and with what arguments.
- **Effort.** About 40 hours: new facts in the extractor, one Datalog rule set, one question template. No new cut or calibration code.

Reflection is the fallback if callback holes rarely sit on source–sink paths; F-Droid apps use little reflection, so it is second choice. A second client analysis (for example Java web apps with servlet sinks) is left to the OOPSLA version.

## Cost

Expected spend is about $430 ($330 in model calls, $100 in compute), with a ceiling of $700 including 50% contingency. Time is the real constraint: about 420 person-hours, or 28 hours a week alongside the internship.

**Money.** Sonnet 5 at $2 / $10 per million input / output tokens; compute on a 16-vCPU, 128 GiB machine (AWS r7i.4xlarge, $1.06/h), which the 26 apps over 12 GB need.

| Item | Assumption | Estimate |
| --- | --- | --- |
| Jev pricing | \~126k questions × $0.00002 | $3 |
| Sonnet 5 answer key, new methods | 6k calls × 3k in / 600 out | $72 |
| Sonnet 5 stated confidence (B5) | 10k calls × 2k in / 300 out | $70 |
| Sonnet 5 self-consistency (B5) | 2k methods × 5 samples | $70 |
| Sonnet 5 witness tests | 1,500 holes × 2.5 attempts × 5k in / 1.2k out | $83 |
| Sonnet 5 witness tests, receipt audit | 400 facts × 2.5 attempts × 5k in / 1.2k out | $22 |
| Jev pricing, callback holes | ~20k questions | under $1 |
| GPU for the open-weight pricer | 10 h × \~$1.50 | $15 |
| Soufflé, Soot and StubDroid runs | \~260 CPU-hours serial, \~90 h on one 128 GiB machine | $100 ($0 on a lab server) |
| **Total** |  | **\~$430** |

**Time.**

| Work | Weeks | Person-hours |
| --- | --- | --- |
| Scale to 400 apps, fix memory | 1–2 | 40 |
| G1: sound-baseline check (B2) | 2 | 8 |
| Ground truth K1 and K2 | 2–4 | 45 |
| Baselines and pricers | 4–5 | 35 |
| Closing loop | 5–8 | 70 |
| Second hole type (callbacks) | 6–8 | 40 |
| Full runs, ablations, statistics | 8–10 | 45 |
| Audit (incl. 20 h from a second rater) and leak confirmation | 10–11 | 60 |
| Writing and artifact | 11–14 | 80 |
| **Total** | 15 incl. buffer | **\~420** |

The receipt audit sits inside the audit row above (its witness tests reuse the closing-loop harness).

Lean version if the internship leaves less than 28 h a week: drop RQ6, RQ7, self-consistency and the third-party set. That comes to roughly 340 hours and $350.

## Risks and fallbacks

The riskiest check is also the cheapest, so it runs first: does the sound baseline B2 already clear most of what we clear?

| Risk | When it shows | Fallback |
| --- | --- | --- |
| B2 clears close to our 41% (G1 fails) | Oct 11 | Lead with closing (RQ4) and with the verdicts B2 cannot clear; if still thin, aim for OOPSLA round 2. Also report whether 41% is over all leak-free verdicts or only those that depend on holes. |
| Observed error above α on the deletion benchmark (G2 fails) | Nov 1 | Switch to cluster-level calibration (A2). If it still fails, stop and diagnose before building more. |
| Closing finds no leaks and < +15 points (G3 fails) | Nov 22 | The paper leans on RQ2 and RQ3; closing becomes a short section. |
| Apps still exceed 128 GiB | Week 2 | Exclude them and list them with sizes; never drop them silently. |
| Jev cannot be released | Any time | Report Jev and the open-weight pricer side by side; release all prices and graphs. |
| Reviewers cite Bastani et al. 2015 and Zhu et al. 2013 | Review | Related work opens with both; claim only the pricing, the certified rate and closing. |
| Internship load | Any time | Lean version, or move to OOPSLA round 2 (Apr 7, 2027). |
| Callback holes rarely sit on source–sink paths | Week 7 | Switch to reflection holes, or keep callbacks as a short section |
| Receipt audit finds cleared verdicts with a real flow in their receipt | Week 11 | Report them; if the audited rate in a price band exceeds the price, recalibrate that band and rerun RQ2 |

## Sources

- [ISSTA 2027 important dates](https://conf.researchr.org/dates/issta-2027)
- [OOPSLA 2027 rounds](https://conf.researchr.org/track/splash-2027/splashoopsla2027)
- [Claude Sonnet 5 pricing](https://www.anthropic.com/news/claude-sonnet-5)
- [AWS r7i.4xlarge pricing](https://cloudprice.net/aws/ec2/instances/r7i.4xlarge)
- [TaintBench](https://ris.uni-paderborn.de/record/27045)
- [Bastani, Anand, Aiken, OOPSLA 2015](https://trustml.github.io/docs/oopsla15-presentation.pdf)
- [Zhu, Dillig, Dillig, APLAS 2013](https://link.springer.com/chapter/10.1007/978-3-319-03542-0_21)
