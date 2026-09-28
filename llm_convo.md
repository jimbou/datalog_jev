
Planning targeted searches to verify novelty against prior art.
Checking the closest prior work first, since the previous proposal's novelty claims need verifying before building on them.

Searched the web, read 4 pages
Bottom line: The idea from my last answer is already published. It is essentially NESA (OOPSLA'25) from Xin Zhang's group, which is in your own key lab, and they have since extended it with LLMs. The better opening is the kind of error their whole approach cannot represent: false negatives caused by the unsound shortcuts real analyses take. My proposal: have Jev put a probability on every unsound choice the analysis makes. Then bound each clean verdict's miss risk by the cheapest set of those choices it depends on, computed as a min-cut. The bound holds no matter how Jev's errors correlate; it needs only calibration.

Why the previous idea is dead
NESA already does it. NESA turns a Datalog analysis into a probabilistic one and feeds a neural network's estimate of how likely each analysis fact holds into it as soft evidence, a "noisy sensor" of the fact. Replacing GraphCodeBERT with Jev only changes the sensor, which is not a paper.
github
The group has kept extending it. Their August 2026 OOPSLA paper resolves static analysis alarms using Bayesian reasoning and LLMs. Their line also covers question selection, efficient inference, and a theory of abstract interpretation with confidence.
Xinpl
Evidence on internal nodes is not new either. DynaBoost (2021) already treated dynamic-analysis feedback as evidence on internal nodes of the Bayesian network.
ACM Digital Library
The idea was also technically weak. In an over-approximating analysis, imprecision arises where rules merge contexts or paths. Each ground clause can be locally correct while their composition is spurious, so asking Jev about clauses one at a time misses it. NESA reports the symptom itself: approximate analysis rules create false correlations between facts.
github
Collision risk. Their affiliation is the Key Laboratory of High Confidence Software Technologies at PKU, the same lab as yours.
ACM Digital Library
The gap they structurally can't reach
Their model can't see missed facts. In NESA, any fact the non-probabilistic analysis cannot derive has probability 0. PLDI'26 defines confidence as the probability that a sound abstract interpreter is locally complete, which is a precision measure on sound analyses.
github
github
Deployed analyses aren't sound. They take shortcuts on reflection, library models, callbacks, native code, and dependency injection. In one Android study, even call graphs built by class-hierarchy analysis recalled only 21–67% of the edges observed dynamically. False negatives from these shortcuts sit outside the derivation graph, so no amount of Bayesian inference over that graph sees them.
arxiv
Calibration only matters on this side. A ranking is unchanged by any monotone distortion of a single score, and only mildly affected when scores are combined. A risk bound inherits every calibration error directly. Jev's one distinctive property is mostly wasted on alarm ranking and essential for bounding soundness.
The idea: priced soundiness
Setup.

E is the set of facts extracted from visible code; R is the analysis rules.
At every unsound shortcut (a "hole"), the analysis enumerates a candidate superset C that is guaranteed to contain the truth:
reflective targets, filtered by cast and receiver types;
for each library method without code, a menu of flow atoms (arg_i→ret, arg_i→this, this→ret, …) whose union over-approximates any behavior;
lifecycle callbacks for each registration.
The true hole facts are some unknown T ⊆ C.
Jev prices every candidate: a Noul per candidate, or a Choice only when exactly one candidate can hold. All candidates at one site go in a single call.
The believed world is S = {e ∈ C : p(e) ≥ τ}. Run the precise analysis on E ∪ S and report its alarms.
Residual risk of an unreported sink q is r(q) = Pr[q ∈ R(E ∪ T)], the probability that q would have been reported had the analysis known the truth.

Theorem. Take any H ⊆ C such that removing H blocks every derivation of q (q ∉ R(E ∪ (C∖H))). Then r(q) ≤ Σ_{e∈H} p(e).

Proof. If T contains nothing from H, then T ⊆ C∖H. By monotonicity, q ∉ R(E ∪ T). So q being real implies T hits H, and the union bound gives the sum. No independence is assumed, either among candidates or among Jev's errors. With calibrated p, the bound holds on average across verdicts.

Computing the bound. The tightest H is the minimum-weight set of removable candidate facts that makes q underivable. Database theory calls this weighted resilience: the minimum number of facts to remove from a database to make a query false. For path queries, it is polynomial for local languages and NP-complete for some other language classes.
arXiv
Northeastern-datalab

Three consequences.

Relaxing stays valid. A cut computed on any coarser analysis R' ⊇ R is also a cut for R.
Relax to a flow graph where code edges can't be cut and candidate edges have capacity p(e). The bound is then a max-flow computation, which is polynomial.
For tighter bounds, solve an integer program over the precise provenance. Any feasible solution is already a valid bound, so you can stop at any time.
The cut is the deliverable. A verdict reads like: "This sink is safe unless one of these 3 reflective targets or 2 library flows is real; total price 0.8%." That is an auditable receipt. It also gives your earlier Assumption Ledger framing a checkable semantics: the cut is the ledger, and Jev supplies the prices.
Refinement goes where it matters. Send only cut facts to slower, more careful checks: a targeted dynamic test, an LLM agent, or a human.
A candidate confirmed false lowers the bound.
A candidate confirmed true moves into E and may produce a new alarm.
Either way, the checking budget is spent exactly where the verdict depends on it.
Why both components do real work
Datalog.

Monotonicity makes unsoundness exactly "missing input."
Provenance tells you what to cut.
Relaxation preserves soundness of the bound.
Jev.

The analysis enumerates the candidates, so bounded typed answers lose nothing.
It works zero-shot across very different kinds of holes.
It is cheap enough to price every candidate and to average repeated calls.
Caveat: its calibration holds only on average across many answers, and its probabilities drift slightly from call to call. Use the per-option probabilities rather than the confidence field, which reflects how concentrated the distribution is, not whether it is correct.
OpenRouter
OpenRouter
Novelty against the closest work
Bayesian program analysis (Bingo, NESA, PLDI'26) estimates the precision of sound analyses. This estimates the soundness of unsound ones. The two are duals and don't overlap in what they measure.
PSP (Parasaram, Barr, Mechtaev, Böhme, ASE'23) is the closest in spirit. It uses execution samples to buy precision at the cost of a small probability of unsoundness. Its probabilities come from executions, so it cannot price behavior you never run, such as unmodeled libraries or unreached reflection. It also produces no compositional per-verdict bound. Cite it prominently.
IEEE Xplore
LLM spec inference (IRIS and successors) plugs specs in as hard facts, leaving the unsoundness unquantified.
Bastani et al. (active learning of points-to specs; eventually sound analysis) reduces unsoundness but doesn't bound it per verdict.
The soundiness manifesto called for evaluating unsound analyses against observed dynamic behavior. This work turns that call into per-verdict numbers.
Yanniss
As far as I found, the link between resilience and residual soundness risk is new. Verify two things before committing: any unpublished work from the lab group, and Böhme's residual-risk line on the fuzzing side.

Where it breaks
Calibration in the low tail. The min-cut deliberately picks Jev's most confident "no" answers, so the bound's validity depends on calibration for p < 0.05, not on overall calibration error. Recalibrate per type of hole, and average several calls per candidate.
Vacuous bounds. If the relaxation connects source to sink through code edges alone, the cut is infinite. Many small-p edges also add up. This is the make-or-break empirical question.
Candidate completeness. T ⊆ C assumes a closed world and a library menu whose top element covers every behavior.
Validation needs complete ground truth. Dynamic traces under-approximate the truth, so you cannot validate an upper bound on real apps alone. Use suites with known ground truth: Judge (ISSTA'19), DroidBench's reflection and ICC categories, and flows injected into real apps.
The race. The dual is an obvious next step for the lab group. Collaborating or moving fast is your call.
Kill test (about 2 weeks)
Run a Soufflé taint analysis on 3–5 reflection- and library-heavy Java or Android apps.
Handle two kinds of hole: reflection and library flows.
Use a context-insensitive flow-graph relaxation, one Noul per candidate, and max-flow for each unreported sink.
If most sinks get bounds above roughly 0.2, the certified version won't carry a paper. The fallbacks are point estimates that assume independence (a weaker paper) or narrowing to fewer kinds of hole.

Working title: Soundiness with Receipts: Pricing Unsound Choices in Datalog Analyses with a Calibrated Decision Model.

Sources:

NESA, OOPSLA'25
Abstract Interpretation with Confidence, PLDI'26
Xin Zhang homepage
On Abstraction Refinement for Bayesian Program Analysis (affiliation)
DynaBoost, FSE'21
PSP, ASE'23
Resilience for RPQs, PODS'25
Unified Reverse Data Management
Call Graph Soundness in Android
Soundiness manifesto
OpenRouter: What Is Jev?
Pasted text.txt
Pasted text.txt
TXT
Searched the web, read a page
The critique is right on the main point, and its recommendation (keep the cut certificate, make post-selection validity the central problem) is the right one. My claim that the bound holds on average across verdicts was false. Praline was a real omission, and I overstated the gap to PSP. One point is aimed at a proposal I never evaluated.

Conceded
Selection breaks calibration. I assumed that choosing the cut from scores and graph structure alone, never from truth, was enough. It isn't, because structure can correlate with truth. The counterexample shows perfect marginal calibration producing a 1% bound on verdicts that are always wrong. Per-fact validity conditional on everything the cut depends on isn't obtainable without strong distributional assumptions, so the guarantee has to come from calibrating the whole procedure.
Jev's calibration no longer drives the argument. Once validity comes from end-to-end calibration, Jev's calibration affects only power: how many clean verdicts you can accept. My "calibration is load-bearing" argument is gone. Jev becomes a replaceable scorer whose case is cost per candidate, and the paper has to show it earns that place.
Praline. It formulates inference as constrained optimization that yields sound, precise bounds for output facts, and adds a δ-exact algorithm using constraint solving, static analysis, and iterative refinement for scale. In practice it runs on SCIP and Z3.
PSP. It does estimate unseen states by spreading probability from fuzzing observations. Its per-assertion upper bound is min(1, sum over states), the same union bound applied to states instead of facts. The defensible distinction is narrower: its implementation cannot estimate assertions at statements the fuzzer never visited, and it has no notion of omitted models composed through derivations.
"Structurally cannot see missing facts" was overstated. Give NESA or Praline the candidate universe and they can reason over it.
The implementation table is right on every row.
Tests can only witness that a fact holds, never that it doesn't.
An LLM check is more evidence, and it belongs inside the calibrated procedure.
Checking some facts changes the probabilities of the rest.
The guarantee is relative to the completed analyzer.
Summary coverage has to be proven against the analysis's abstract effects: heap writes, statics, callbacks into app code, exceptions.
Misdirected
My "already published" verdict was about my own first design: Jev scores as soft evidence for Bayesian alarm ranking, which is Li and Zhang's mechanism. I haven't seen the error-tolerance certificate proposal from your other thread, and nothing I said rules on it. There are indeed two NESAs; Wang et al.'s is a restricted Datalog policy language that splits an analysis into sub-problems handled by parsing or LLM prompting.

Three additions

1. The tight bound, and where the cut is exact. Suppose you have valid per-fact probabilities but no correlation information. Then the best sound bound on P(q) is min(1, τ*), where τ* is the fractional minimum-weight hitting set of q's explanations.

Why it's an upper bound: any fractional hitting set is feasible for the dual.
Why it's tight: a fractional packing of explanations, under capacities p(e), builds a joint distribution that attains it.
This is my derivation; check it against Praline's formulation before relying on it.
Consequences:

Reachability, one candidate per edge. The LP is integral, so max-flow computes τ*exactly. Here the critique's integral cut is the optimum, not a relaxation.
One library summary shared across call sites. This is a label s-t cut, which is NP-hard and hard to approximate. Its LP relaxations have large integrality gaps, so even an optimal integral cut can sit far above τ*.
Against Praline. On the first fragment both methods reach the same optimum, so the comparison is cost only. On shared summaries both face hardness, so compare cost and tightness. Praline is strictly tighter when you can supply extra correlation structure the cut ignores, such as mutually exclusive targets at a single-valued reflective site. Measure how much that matters.
2. Exact labels by simulating holes.

Method. Mask code you actually have: library bodies, reflection sites a string analysis can resolve, framework callbacks with precise models. Run the pipeline, then label each verdict with the completed analyzer on the unmasked program.
Payoff. Labels are exact for the relative guarantee, mechanical to produce, and plentiful.
Risk. Shift: what you can mask differs from what is genuinely missing, such as native code and dynamic loading.
Shift check on real holes. Label the surrogate "some cut fact is true." This is conservative, since any miss requires a true fact in the cut, and a human adjudicates only the facts in each cut. Human "false" rulings can be wrong, so treat this as a diagnostic, not a guarantee.
3. Conformal selection, with programs as the unit. Accepting a batch of clean verdicts is a selection problem. Conformal selection controls the false discovery rate of the selected set when calibration and test data are jointly exchangeable.

Use the cut value as the score.
Put τ, refinement, and escalation all inside the calibrated procedure.
The exchangeable unit must be the program. Verdicts in one program share candidates, which is exactly the dependence the counterexample exploits. Hierarchical variants exist.
You need hundreds of programs, which hole simulation over a large corpus makes feasible.
Learn-then-Test remains the tool for tuning parameters like τ.
Revised claim
For each unreported query, the method produces three things:

a checkable set of omitted facts, at least one of which must hold for the completed analyzer to report the query;
the tightest distribution-free bound over that structure, computed exactly by max-flow on the reachability fragment;
an acceptance procedure with finite-sample FDR control over clean verdicts, calibrated on simulated holes.
Experiments
Inference. Using exact probabilities from simulated holes, compare the cut against Praline: cost on the reachability fragment; cost and tightness on shared summaries.
Validity and power. Using learned scores, measure realized FDR on held-out programs and the acceptance rate. Compare Jev, a cheap classifier, and an LLM, per dollar.
Shift. Compare simulated and real holes using surrogate labels.
Kill criterion: at α = 0.05, if fewer than a fifth of truly clean verdicts get accepted, the procedure is valid but useless.

Sources:

Praline (arXiv)
Praline as a baseline (SCIP/Z3)
PSP, ASE'23
NESA, Wang et al., FSE'26
Selection from Hierarchical Data with Conformal e-values
Selection by Prediction with Conformal p-values
Minimum Label s-t Cut has Large Integrality Gaps
Integrality gaps (Inf. Comput.)
