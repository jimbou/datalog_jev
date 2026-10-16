# Framing memo (2026-10-16)

Purpose: one story (gap -> idea -> evidence), one experimental grid, five RQs. Replaces the ad-hoc order in which
the experiments were done with the order in which a reader needs them.

## 1. The thesis in one sentence

> An unsound static analysis can be given a certified, per-program bound on how often its clean verdicts are wrong,
> by treating an LLM's library knowledge as an *untrusted score* (a price on a min-cut receipt) rather than as a
> *fact*, and certifying a threshold on that score with distribution-free risk control.

Everything else in the paper is either the mechanism that makes this possible or the evidence that it works.

## 2. The gap, stated as a 2x2

Prior answers to unmodeled library code differ on two axes:

| | Verdict carries **no explanation** | Verdict carries **its library assumptions** |
| --- | --- | --- |
| Library oracle **trusted as fact** | FlowDroid summaries, StubDroid, Atlas, Merlin/Seldon, IRIS, SemTaint, LLMDFA, DAInfer, CPGHunter | -- |
| Library oracle **not trusted** | sound over-approximation (assume all flows; no oracle needed) | Bastani et al. cuts (a person checks every assumption; no probabilities, no guarantee) |

The empty cell: assumptions are named *and* priced by an oracle *and* the oracle is not trusted, because the error of
the accepted verdicts is certified on programs. Praline gives probabilities but trusts its inputs; conformal
selection gives a guarantee but per verdict, which we show is the wrong unit for program analysis.

Web check (2026-10-16): no published work applies conformal prediction or Learn-then-Test to static-analysis verdicts;
no LLM-spec paper reports calibrated confidence or an error bound. Add DAInfer (FSE'24, API aliasing specs) and
CPGHunter (EMSE'26) to the "taken as fact" paragraph.

## 3. What is genuinely new, and what is borrowed (say both plainly)

New:
1. The **problem formulation**: (alpha, eps)-soundiness, per program, relative to a key, oracle-agnostic.
2. **Receipt = score**: the min-cut over priced holes as a selection score, with the tightness result (no cleverer
   structural bound exists without correlation knowledge). Small theorem, but it closes the "why not Praline" question.
3. **Oracle-agnostic certification**: the LLM only orders verdicts; validity comes from the calibration. The
   empirical consequences are the paper's most interesting findings: AUROC does not predict usefulness (only the low
   end of the order matters), cheap models that answer too confidently clear nothing but never break the guarantee,
   per-verdict selection misses its own target.
4. **Budgeted checking** as a direct use of receipts (which facts to check, without looking at answers).

Borrowed, cite without apology: min-cuts over flow graphs (Bastani), union bound, LTT fixed-sequence testing,
LLM-as-library-oracle (IRIS). The contribution is the combination and what it buys; reviewers accept that when it is
stated, and punish it when it is hidden.

Intro contribution list (replace the current four):
- C1 Definition of (alpha, eps)-soundiness (unit = program; relative to a key).
- C2 Priced receipts: min-cut score, tightness, and a certified threshold valid for any pricer.
- C3 An empirical study on 307 F-Droid apps against 5 baselines, 8 keys, 10 pricers, with ablations of every
  component (unit, pricer, question, bound, calibration).
- C4 Two uses of receipts beyond clearing: budgeted checking, and graceful degradation of the analysis on apps that
  do not fit (code that is not analyzed becomes priced holes).

## 4. The experimental grid (what makes it look standard instead of patched)

Fix one **default configuration** and print it once in Setup; every table varies exactly one factor from it.

| Factor | Default | Varied in |
| --- | --- | --- |
| Apps | 307 main F-Droid apps | RQ5 (rescued large apps, malware, second population) |
| Key | main key (two-model agreement + FlowDroid models) | RQ2 (8 keys) |
| Pricer | Jev | RQ3 (panel), and the fixed baseline panel in every table |
| alpha / eps / splits | 0.05 / 0.1 / 200 half splits | RQ2 (alpha 0.02, 0.1; eps; 30/70) |
| Score | union bound on min-cut | RQ3 (max, product, distinct facts) |
| Unit | program | RQ3 (verdict = conformal selection) |

Fixed **row set** that appears in every results table, in this order, always with the same two columns
(cleared share of hard slice, held-out apps wrong) plus "real leaks kept" where it matters:

1. Sound (open all holes): 0% cleared, 0% wrong. Anchor.
2. Unsound (FlowDroid models only, trust clean verdicts): 100% cleared, 97% of apps wrong. Anchor.
3. Counting (Bastani cut size, no prices).
4. LLM as fact (yes/no answers used as models, IRIS-style): **on the main key too**, using Jev at 0.5 and GPT labels
   (not Sonnet, which is in the key). Today this baseline appears only on deletion keys in prose: it is the most
   natural competitor and must sit in the main table.
5. Uncalibrated bound (delta = alpha).
6. Conformal selection per verdict.
7. Receipts, frequency prior / classifier / Sonnet 5 / Jev (ours).

Columns reported with the 5th-95th percentile over splits everywhere, not only in the sensitivity table.

## 5. Five RQs

Move the current RQ1 (prevalence: FlowDroid loses 82% without models; a third of real leaks need unmodeled methods;
FlowDroid confirms 43 of 58 receipts) out of the evaluation into Section 3 as "How much is at stake". It motivates
the problem and is not an evaluation of the approach. The RQs then all test the thesis:

- **RQ1 Effectiveness.** How many hole-dependent clean verdicts do priced receipts clear at a certified risk, and at
  what cost in missed leaks, compared with the baselines? (current RQ2 + B3 per-app alarms + leaks kept + cost/time
  per app). One table, the fixed row set, the main curve.
- **RQ2 Validity.** Does the certified error hold when the key, the pricer, alpha, eps, the calibration size or the
  split grouping changes? (current RQ3 + the sensitivity rows of tab:unit + the "guarantee still holds" halves of
  RQ4). Message: validity never moves; clearance does. One table: keys x pricers; one line per sensitivity.
- **RQ3 Ablations: what determines clearance?** Unit (program vs verdict), pricer (panel; AUROC vs low end of the
  order), question wording, combination of prices, calibration floor. (current RQ4 + the unit paragraph of RQ2).
  This is the section reviewers call "ablation study"; name it so.
- **RQ4 Receipts in use: checking facts.** Budgeted checking (current RQ5), per-app alarms after 25/100 checks,
  checks per app. If C3 (second rater) is done, the human agreement numbers go here or in Setup.
- **RQ5 Beyond the calibration setting.** Same protocol, threshold certified on the 307 apps, applied to:
  (a) the 66 rescued large apps where bundled libraries are holes (graceful degradation; FlowDroid same-budget
  control as one sentence); (b) TaintBench malware; (c) a second population (IzzyOnDroid or AndroZoo) when F3 is
  done; (d) another hole type (Intent edges, now in Discussion). One table with a row per population: apps, decided
  verdicts, cleared, apps wrong, leaks the key says are in scope. This is where every "patch" (fallback, R8, server
  entries, FlowDroid budget) gets a single home and a single protocol.

Abstract and intro then quote RQ1's numbers and one sentence each for RQ2-RQ5. Today the abstract carries nine
numbers from six experiments, which is what makes the work read as patches; the 442-vs-317 coverage claim in
particular should leave the abstract and live in RQ5/Discussion.

## 6. What is still missing (ordered by value per day)

1. **LLM-as-fact baseline on the main key** (half a day, no new pricing): Jev at 0.5 and GPT labels as models.
   Without it the main table lacks the obvious competitor.
2. **Second human rater on 30-40 facts, Cohen's kappa** (C3, hours): the key's credibility rests on 60-67 facts
   checked by one author.
3. **Cost and time paragraph** (hours): price per app per pricer, min-cut and certification time, and the one-off
   cost of a key. Reviewers always ask; the numbers exist.
4. **Second population** (F3, a week): the definition is about a distribution D; calibrate-on-F-Droid,
   test-on-IzzyOnDroid is the experiment the definition begs for and answers the "small open-source apps" threat.
   Higher value than F4.
5. **Reproducible pricer** (C1): Jev is a black box behind a commercial API. State in Setup what is known about it,
   keep Sonnet 5 as the pinned, rerunnable pricer in every table, and if the sonnet55def3 run (F2) clears more than
   17%, promote it. Do not let F2 grow beyond the dev-subset discipline already in place; report all variants in one
   ablation row group.
6. **F4 malware/callback holes**: only if a week is free. The honest finding (6 leaks excluded by the flow
   definition, receipts make it visible) is enough for RQ5(b).
7. Drop or demote: B2 (certify on FlowDroid) stays a validation sentence; C0 server entries is a footnote.

## 7. Related-work paragraph order (mirror the 2x2)

1. Soundiness (the manifesto; we quantify it).
2. Library models, hand-written and inferred (trusted; complementary).
3. LLMs as library oracles (IRIS, SemTaint, LLMDFA, DAInfer, CPGHunter): trusted as fact; our baseline 4.
4. Assumption listing and abduction (Bastani, Zhu, Dillig): named but unpriced; our baseline 3.
5. Probabilistic analysis (Praline): priced but trusted; tightness result.
6. Distribution-free risk control (LTT, conformal selection): the tool; our unit result.
Keep the table, but relabel columns to the 2x2 axes: Explains / Prices / Oracle untrusted / Guarantee unit.
