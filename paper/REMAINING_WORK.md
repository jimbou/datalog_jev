# Remaining work (consolidated 2026-10-07, updated 2026-10-13)

This file replaces the open items in `paper/PLAN.md` (now historical), the "next steps" in `FINDINGS.md` §23 (stale:
conformal selection, key labels, a second hole type and the Praline check are done) and summarizes
`paper/REVIEW_FIXES.md` (details for items B1-B3). Status of the paper: restructured in the lab's style (commit 757bf0d),
body ends on page 16 of 18, compiles without errors or overfull lines.

Mock-review estimate of acceptance: about 35-40% now (B1 done, B3 part done, rubric key as main key); B2 will most likely
stay a validation; other items add less.

**Done since 2026-10-07 (summary):**

- Rubric relabeling; rubric key is the main key (A1-A5).
- B1: main setting is now our analysis + FlowDroid's models, holes only for the 12,274 unmodeled methods (`fm-`); whole paper,
  tables and figures rewritten for it (new example `de.luhmer.owncloudnewsreader`; RQ1 now "a third of real leaks pass only
  through unmodeled methods"; RQ6 now "only 6 documented malware leaks need unmodeled flows").
- B3 part 1: false alarms per app before/after clearing (RQ2, intro): median 13 -> 6, 81% -> 89% of alarms real.
- B2 step 1: retry of the 89 FlowDroid-failing apps with 55 min and 24 GB (running; 30 of 31 finished apps failed on memory,
  1 rescued with 8 FlowDroid-confirmed receipts). Discussion now explains why we certify on our analysis and validate on
  FlowDroid (runs with open holes exceed memory).
- Framing: receipts complement library models (intro sentence, example, related-work table and paragraph, discussion); the
  paper no longer presents FlowDroid as a competitor.
- Implementation section states that FlowDroid's default source/sink list (2.15.1) contains Java server entries.
- DONE 2026-10-13: same-budget comparison (`bench/fd_budget.py`, `data/fd_budget.jsonl`, summary
  `analysis/fd_budget_summary.py`): FlowDroid on all 585 picked F-Droid apps with our build's budget (2100 s, 16 GB per
  run, 2 runs of 4 threads on 8 cores). Ours built 332 (57%), FlowDroid with its models 317 (54%), with holes open 252
  (43%); holes cost FlowDroid 65 apps (46 timeout, 19 memory). 159 apps finish only with ours, 79 only with FlowDroid with
  holes. Where both FlowDroid runs finish (252), it reports no leak in 191 and holes add sinks in 17. Reach on 142 apps
  where both finish: FlowDroid median 4 sources / 44 sinks, ours 11 / 57. The last 84 apps ran after the server became
  16 cores (pinned to 8; no sign of an advantage). Paper text for RQ1 and the discussion approved 2026-10-13, to be
  written in after F1 (our build count changes).

**Main setting since 2026-10-08:** FlowDroid's models as code (evaluator prefix `fm-`), rubric key as main key (`fm-rk-<pricer>`).

## A. Finish what is running (must do)

A1-A5 are done (rubric relabeling, rubric key as main key, agreement numbers), and so are all `fm-` runs
(`bench/queues/fm_all_chain.sh`, FMA-DONE 2026-10-08 21:11 UTC): the whole paper, its figures and `FINDINGS.md` 22d use them.

| # | Item | Status / how |
| --- | --- | --- |
| A1 | Sonnet rubric relabeling | DONE |
| A2 | Main results under the rubric key | DONE (then redone in the `fm-` setting) |
| A3 | Fill the rubric row of Table 4 and check the RQ3 box | DONE |
| A4 | Final agreement numbers | DONE (90.1%, kappa 0.80; person agrees on 54 of 57 facts where both models agree) |
| A5 | Main key | DONE: rubric key |

## B. Acceptance improvers from the mock review (see `REVIEW_FIXES.md`)

| # | Item | Why | Effort |
| --- | --- | --- | --- |
| B1 | DONE 2026-10-08: holes only where FlowDroid has no model (`fm-` mode), new example (`ContentResolver.insert` leak through unmodeled `ContentValues.put`) | removed the strawman objection | done |
| B2 | IN PROGRESS: certify on FlowDroid itself. Step 1 (retry with 3300 s / 24 GB) running, mostly memory failures. Open: more small apps, tighter class mapping, or certify at alpha 0.1 on all completed apps (zero-loss apps included). See "Building on FlowDroid" in REVIEW_FIXES.md | removes "certified misses of a toy analysis" | server days; will most likely stay a validation |
| B3 | PART DONE 2026-10-09 (alarms per app in RQ2: median 13 -> 6, 81% -> 89% real). Open: triage time, shared checks. Show user value: false alarms per app before/after clearing, apps with no alarms left, receipt size of remaining alarms, shared checks across apps; optional timed triage sample | makes "40% of the hard slice" concrete | about a day; user study optional |

## F. Stronger results without bending the protocol (agreed 2026-10-12)

Rules for all items below: our build never gets more time or memory than FlowDroid (the same-budget setting of
`bench/fd_budget.py`: 2100 s and 16 GB per app, 4 threads, two apps in parallel); apps and populations are chosen
before running, never by our results; variants are chosen on a development subset, and every variant tried is reported.

| # | Item | Why | Effort |
| --- | --- | --- | --- |
| F1 | Make more apps build within FlowDroid's budget (details below) | 253 of 585 apps fail today; the corpus is biased to small apps; Threats section | hours (a-c), then server days |
| F2 | Better pricers, tried on a development subset first (details below) | the pricer decides the cleared share; the question wording alone moved Jev from 9% to 49% | days |
| F3 | Second population: Play apps from AndroZoo (replaces C4) | commercial apps bundle ad and analytics SDKs that FlowDroid does not model: the realistic case where models fall short | weeks; needs an AndroZoo key; works well only with F1e. Fallbacks below |
| F4 | Malware: callback holes and more malware with leaks we can catch (replaces C5; details below) | RQ6 now hurts: all 6 relevant TaintBench leaks are excluded by our own flow definition | about a week for callback holes; malware set depends on access |
| F5 | Lead with the recall side in abstract, intro and RQ2 (details below) | "clears 49% of the hard slice" undersells the same data | an hour |

**F1. More apps within the same budget.** Why apps fail today: `analysis/run_android.py` gives 1200 s to Soot extraction
and then 900 s to Soufflé under a 12-16 GB address-space limit (`RLIMIT_AS`), and the log says only "souffle failed".
The 900 s Soufflé limit is tighter than any analysis-phase limit FlowDroid got (RQ1 used `-dt 2400`). Likely causes:
bundled libraries dominate the analysis (small apps already have millions of points-to facts: `com.ericlowry.dnstoggle`
3.1M, `uk.org.ngo.squeezer` 5.9M, mostly AndroidX/Kotlin code), Soufflé runs as an interpreter, and the rule
`TV(to) :- TV(b), Load(to, b, _)` with context-insensitive points-to spreads taint widely (35k tainted variables in a DNS
toggle app; probably also why we reach only 58% of FlowDroid's leaks at ~1% precision).

- a. Record per app which stage failed and why (extraction timeout or error, Soufflé timeout, Soufflé out of memory),
  in `data/android_failed.txt` or a new file with a reason column.
- b. One combined limit of 2100 s per app (extraction plus Soufflé) instead of 1200 + 900, and 16 GB, so the budget is
  exactly FlowDroid's in `fd_budget.py`; time left over from extraction goes to Soufflé.
- c. Compile `taint.dl` once (`souffle -o`; needs g++ on the server) and check on 5 apps that the outputs are identical.
- d. Retry the 253 failed apps with a-c. Not more time or memory.
- e. Bigger change: treat bundled third-party libraries (AndroidX, Kotlin, Play services, OkHttp, Gson, ...; prefix list or
  a library detector such as LibScout) as library code, so their bodies are not analyzed and their methods become holes.
  The analysis gets much smaller, so more apps fit, and the new holes are methods FlowDroid has no models for, which also
  answers "the pricer memorized Android APIs" (C2). Needs: the library list, calls into these packages as `LibCall`,
  candidate flows for the new methods, key labels (rubric Sonnet and GPT via the CLIs; StubDroid on the library jars for
  K2), prices. **Try first on a subset** (about 20 built and 20 failed apps): build success, time, hole-dependent sinks,
  number of new methods to label, cleared share. Rebuild everything only if the subset looks good. Caveats: every number
  in the paper changes, the cleared share may drop, and FlowDroid does read bundled library code, so state that our
  "library" is code not written by the app's developers, as for the framework.

**F1 status (2026-10-13).** Code: `analysis/run_android.py` options TOTAL_TIMEOUT, REASONS_FILE, SOUFFLE_BIN,
EXTRACT_XMX/EXTRACT_THREADS, LIB_PREFIXES, BUDGET_FILE; `extract/Facts.java` EXCLUDE_PREFIXES/KEEP_PREFIX; queues
`bench/queues/f1_*.sh`, `f1e_*.sh`; results (no graphs) in `data/f1/`.

- a. DONE: reason and seconds per app (`data/f1/reasons*.tsv`). The old build recorded no reasons.
- b. DONE: 2100 s shared, 16 GB (Soufflé address space; Soot heap now also 16 GB), 4 threads, 2 apps on 8 cores.
- c. TRIED, NOT USED: compiled taint.dl gives identical graphs and identical per-sink results on 6 check apps, but on
  systems.sieber.remotespotlight (4 threads) interpreter 508 s / 13.9 GB max RSS, compiled 1153 s / 12.8 GB, compiled with
  `souffle -j 4` 461 s / 16.0 GB (over the limit once). Rebuilt graphs differ from the paper's by a few nodes (Oct 6
  `cls:` edit) with identical evaluation results.
- Bug found: the extractor omits a relation file when an app has no fact of it (e.g. SStore), and Soufflé then refuses to
  start; fixed in `prepare()` (empty files). Rescues app.rapidsplit (trivial graph).
- d. DONE (2026-10-13 04:18 to 20:59, restarted 06:11 with the fix): 253 failed apps, 12 built, 241 out of memory
  (all in Soufflé), so memory is the bottleneck, not time.
- e. Subset DONE (`data/f1e_subset.tsv`, 20 built + 20 failed, seed 20261013; prefixes `data/bundled_libs.txt`, fixed
  before results). Built apps: sources 181 -> 68, sinks 923 -> 441, hole-dependent sinks 5,490 -> 1,317 (most sources and
  sinks sit inside bundled libraries; in 4 apps all sources go): rejected for all apps. Failed apps: 8 of 20 build, and all
  8 run out of memory without step e (attribution run, `data/f1/reasons_attrib.tsv`). Minified apps (e.g. app.devswitch,
  96% renamed classes) gain little from prefixes.
- e as fallback: DONE (2026-10-13 20:59 to 2026-10-14 06:23, `bench/queues/f1e_fallback.sh`): the 241 apps still
  failing got step e with only the time their full attempt left (2100 s minus its recorded seconds), 16 GB, so the per-app
  budget stays FlowDroid's. 98 built, 143 out of memory. In all: 110 of the 253 rescued (12 by d, 98 by e).
- FlowDroid with the same budget on these 253 (`data/fd_budget.jsonl`): succeeds on 103 (21 with a sink). Ours 110: 83 both,
  27 only ours (3 retry, 24 fallback), 20 only FlowDroid. All 585 picked apps: ours 344 without step e, 442 with it
  (step e apps analyze bundled libraries as holes, FlowDroid analyzes their code), FlowDroid 317.
- New hole methods of the rescued apps (`probes/extend_holes_fw.py` with LIB_PREFIXES, appended to
  holes_android_fw.jsonl on the server, backup .bak): 10,503 (340 framework, 10,163 bundled-library: androidx 5,926,
  kotlin 1,303, kotlinx 542, ...), 8.8 candidate flows per method vs 2.9 before; 66 of the 98 fallback apps have library
  holes (median 80, max 1,278), 8,037 methods occur in one app. 10,149 need rubric labels.
- Labels and prices RUNNING (2026-10-14, `bench/queues/f1_label.sh`, `f1_label_gpt.sh`, `f1_label_gpt4.sh`): Sonnet rubric
  labels then sonnetp prices via Claude Code; luna prices via Codex; GPT rubric labels (gpt-6.1-sol; it returned 429 at
  first, 2 threads, 4 after luna) via Codex. OpenRouter prices DONE (approved, `bench/queues/f1_price_or.sh`, cap $10):
  $9.17 (Jev choice-obj $0.62, taint $0.36, choice $0.55; q27 $2.20, qflash $0.30, dsflash $0.86, gflash $4.29). q27,
  qflash and dsflash now reason by default on OpenRouter (slow, up to 50x the cost): their default pass was stopped after
  a few minutes and they were priced with NO_REASONING=1, the setting of the old fill-in pass (old cost per method
  matches). Jev fails on 4 methods (522 to 1,204 candidate flows; price 0.5). K2 for library methods (disagreements)
  would need StubDroid on library code from the APKs. Then decide whether rescued apps enter the corpus; report them apart
  (retry, fallback) and merged.
- Labels DONE 2026-10-15 03:00: Sonnet 10,148 of 10,149, GPT 10,149. Where both decide, Sonnet vs GPT agree as before
  (kappa 0.82 on the new library methods, 0.80 old), but GPT answers U (undecidable) for 27.2% of library candidate
  flows (Sonnet 0.3%), so 27.4% of library flows are unknown in the key before K2. luna prices DONE; sonnetp running
  (8 threads from 03:20, about 7.5 methods/min).
- First main evaluation (fm-rk-choice-obj, `bench/queues/f1_eval.sh`, threshold certified on all 307 main apps; alpha
  0.05 -> delta 0.2, alpha 0.1 -> 0.3). Cleared share of leak-free hole-dependent sinks, apps with a false accept:
  main 47.3%, 1/307 | retry 10 apps 48.6%, 0/10 | fallback 56 apps 41.5%, 0/56 (undecided 18.2% of sinks) | fallback
  without the 17 misattributed apps 41 apps 54.9%, 0/41. At alpha 0.1: main 60.1% 12/307, retry 54.7% 1/10, fallback
  55.3% 1/56 (dev.bg.skylib). Only 66 of the 110 rescued apps have decided hole-dependent sinks.
- All prices DONE 2026-10-15 08:34 (sonnetp via Claude Code, 8 threads, 0 errors). Every main pricer on the rescued apps
  (`data/f1/eval_summary.txt`, `analysis/f1_score.py`; threshold certified on all main apps per pricer, alpha 0.05):
  Jev 47.3% main / 48.6% retry / 41.5% fallback / 54.9% fallback-17, no false accepts on rescued apps; Sonnet 16.7% /
  15.1% / 11.9% / 13.7%, but 2 of 56 fallback apps with a false accept (com.wirelessalien.android.moviedb,
  xyz.hisname.fireflyiii), both through one atom: androidx AppCompatActivity.setContentView(View) arg0 -> this, labeled
  a flow by both labelers, Sonnet price 0.02 (on the main corpus androidx is app code, so this hole never occurs); freq
  19.0% / 13.4% / 12.9% / 11.5%; b6 and counting clear nothing at alpha 0.05, as on the main corpus.
- AGREED 2026-10-15: the fallback becomes part of the pipeline (full build; on the memory cap, step e with the time
  left), positioned as graceful degradation: what does not fit becomes priced holes and the bound still holds. Main
  tables stay on the 307 apps; add a pipeline row and the coverage claim. LTT with 200 splits on main + rescued (373
  apps), alpha 0.05: Jev 1.3% held-out apps wrong (main 0.9%), power 49.6% (48.7%); Sonnet 0.5% (0.0%), 16.3% (16.7%);
  freq 0.0%, 18.4% (19.0%). Coverage on the 585 picked apps: FlowDroid 317, ours 344 without the fallback, 442 with it.
  Disclose that the fallback was chosen after the 40-app subset (prefix list fixed before any step-e result).
- FlowDroid control RUNNING (2026-10-15 08:53, `bench/fd_fallback.py`, `bench/FDExclude.java`, `bench/queues/fd_fallback.sh`):
  FlowDroid with the same prefixes excluded (Soot exclude list, app package kept), 151 out-of-memory apps with the time
  left (fallback), then the 107 successful apps with sinks at 2100 s (control: leaks lost without notice).
- Step-e threat found: R8 moves app code into library-named classes (e.g. `okio.Okio.HomeScreenContent(...)`, a Compose
  screen of com.ammar.wallflow), so prefixes treat some app code as library code. Lower bound (library holes whose
  signature names a type of the app's package): 224 of 10,163 methods (2.2%), 9.6% of candidate flows, 17 of the 66 apps
  with library holes (top: com.ammar.wallflow 64 of 760, org.equeim.tremotesf 39, com.readrops.app 37). Labels and
  prices for such methods have no API contract to go by. Report fallback apps with and without these 17 at least.

**F2 cost (measured 2026-10-15).** Methods to price (unmodeled holes): dev subset (92 apps) about 5,300; all 307 main apps
7,518; main + rescued 17,894. Claude Code is a subscription with usage limits; one pricing call is about $0.009 in
API-equivalent usage (measured with `claude -p --output-format json` on 10 methods with 1 to 9 candidate flows; library
methods cost more). Jev with the written definition: about $0.3-0.5 (dev), $0.5-0.8 (all main), $1-2 (main + rescued),
OpenRouter, needs approval. Sonnet with 5 samples: 26,500 calls (dev, about $240 equivalent, about 18 h at 8 threads),
89,000 calls for main + rescued (about $800 equivalent, about 60 h): too much of the subscription. Sonnet with 1 sample on
the dev subset: about $50 equivalent. Combinations of existing prices (Jev with ties broken by the classifier,
max(Jev, Sonnet)): free. Recommended: Jev with the definition plus the free combinations; no 5-sample Sonnet run.

**F2. Pricers on a development subset.** Fix a random 30% of the 307 apps (seeded) as development apps; choose the variant
there; report the chosen variant with the usual 200 splits on all apps and on the other 70% alone, and list every variant
tried. The guarantee holds for every variant (Proposition 2); the dev subset only guards against choosing on the test
data. Price only the methods on the dev apps' receipts first.

- Jev with the full written flow definition (Appendix A) in the question. Jev does not label the key, so this is not
  circular. Needs approval for OpenRouter spending (about $0.4 for the whole corpus, less for the subset).
- Sonnet 5 with the written definition, about 5 samples per method via Claude Code (free), price = the highest sample,
  against its low prices for some real flows. Sonnet with the definition is close to one of the two labelers of the main
  key, so judge it mainly under K2, the deletion keys and the GPT-only key.
- Combinations: Jev's price with ties broken by a second score (Sonnet or the classifier), and max(Jev, Sonnet). Jev's
  prices sit on few values, so the risk curve jumps right after 0.2 (held-out error 0.9% against a 5% target, and
  30% vs 70% calibration changed clearance by under a point); breaking ties may let the threshold sit between steps.

**F3. Second population and fallbacks without AndroZoo.** Apply for the AndroZoo key first (university email, usually
days). Whatever the source: fix the app list before running (store, date, size limit, seed), and put only SHA-256 hashes
in the artifact, not the APKs (stores and AndroZoo forbid redistribution). Fallbacks, best first:

- IzzyOnDroid repository: F-Droid-style, so our F-Droid download tooling should work with only the repository address
  changed; no account. Developer-built apps that often bundle Firebase, ads and analytics SDKs. Cheap enough to try
  next to the F1e subset trial. Related: F-Droid apps with the anti-features Tracking, Ads or NonFreeNet (chosen by
  metadata, but still F-Droid).
- Chinese stores (Huawei AppGallery via `apkeep`, Xiaomi, Tencent MyApp): commercial apps with SDKs FlowDroid does not
  model (Umeng, JPush, Bugly, ad networks), fast to reach from the PKU server. Many are packed or obfuscated, so Soot may
  fail; only with F1e.
- Google Play via `apkeep` and a Google account: the population reviewers expect, but Google's terms forbid automated
  downloads and the account can be blocked. Only a small list fixed in advance, and only if the user and supervisor agree.
- CICAndMal2017 / CICMalDroid 2020 (University of New Brunswick) include benign Play apps; check whether the benign APKs
  can be downloaded; they are from 2017-2020.

**F4. Malware.**

- a. Callback holes, built like the Intent holes (`taint_icc.dl`): edges from an object registered with the framework
  (`WebView.addJavascriptInterface`, listeners) to the parameters and return values of its callback methods. Puts 3 of
  the 6 TaintBench leaks in scope. Decide whether callbacks join the flow definition or stay a separate hole type with its
  own key, as Intent holes are.
- b. More malware with documented leaks: DroidBench 3.0 and ICC-Bench (small, documented, include callback and library
  cases), UBCBench, and malware families whose reports say what data they steal (AMD dataset family descriptions,
  MalGenome/Drebin). Samples without AndroZoo: MalwareBazaar (abuse.ch), VirusShare, Koodous (free accounts; family
  tags, no leak lists, so pair them with published family reports). Choose apps by their documentation before running. For every sink our analysis reports through an
  unmodeled method that FlowDroid's models miss, a person confirms or rejects it in the decompiled code (jadx); report
  the number checked, confirmed and rejected ("leaks that FlowDroid's models miss and receipts report, confirmed by hand").
- c. If a and b give little, shorten RQ6 to the transfer result.

**F5. Recall-side headline.** At the threshold certified on all apps, the analysis reports all but one of the 22,888 real
leaks that FlowDroid's models miss, while adding half of the false alarms that a sound treatment adds. State with it that
"real" means real on our flow graph, which comes from an analysis less precise than FlowDroid (Discussion). Also add the
per-app false alarms after 25 and 100 checks (RQ5), and the per-app cost of checking 25 facts once for the whole corpus
(about 0.08 checks per app).

## C. Further strengtheners (lower priority)

C0 (2026-10-08): FlowDroid's default source/sink list (2.15.1, which we use unchanged) contains Java server entries; some occur
in Android apps (`String.replace` as a sink, `File.getAbsoluteFile` as a source). The paper now states this (impl). Open:
measure the share of verdicts at such entries and, if large, add an Android-only sensitivity run (graph rebuild).

| # | Item | Why | Effort |
| --- | --- | --- | --- |
| C1 | Reproducible main pricer: report a pinned, rerunnable model next to Jev (Jev is a commercial service with an undisclosed model) | Verifiability criterion | days (pricing via Claude Code/Codex is free per call but not deterministic; an open-weight model run locally would be best, but the cheap open models we tried price too confidently) |
| C2 | Pricer on less-known code: hide bundled third-party libraries (OkHttp, Gson, Guava, Jsoup) or label them with StubDroid, and measure the pricer there | answers "the LLM memorized Android APIs"; now part of F1e | about a week |
| C3 | Second human rater on ~20-40 facts for an agreement statistic (Cohen's kappa) | key quality | a few hours of a colleague's time |
| C4 | Now F3 | | |
| C5 | Now F4 | | |

## D. Paper housekeeping (must do before submission)

| # | Item |
| --- | --- |
| D1 | Check the ISSTA 2027 call (template, page limit, anonymity, AI-disclosure and data-availability rules); we followed ISSTA 2026's |
| D2 | Anonymous artifact link (intro, Data Availability); package code, graphs, prices, keys, audit CSVs, FlowDroid outputs; anonymize `checked_by` in the audit CSVs |
| D3 | AI disclosure (`sections/ai.tex`): exact tool names and versions, agreed by all authors |
| D4 | License and archival repository (camera-ready) |
| D5 | Full read-through by the authors for flow and tone (the text was rewritten in the lab's style; check it does not read as generated), consistent terms ("hard slice", "receipt", "pricer"), numbers against `FINDINGS.md` |
| D6 | Keep the body within 18 pages after B1-B3 (candidates to cut: deletion figure to appendix, wording paragraph to one sentence, Intent-holes paragraph) |
| D7 | Regenerate figures after any rerun: `analysis/paper_stats.py` on the server, then `paper/make_figs.py` |

## E. Decisions only the user can make

- Whether to do B2 (server days, uncertain outcome) and C1/C2 (time).
- Whether a colleague can be the second rater (C3) or join a small triage study (B3 optional).
- Target venue/date (ISSTA 2027 deadline unknown until the call is out).
- F2: approve the OpenRouter spend for Jev with the written definition (about $0.4).
- F1e: after the subset trial, whether to rebuild all graphs with bundled libraries as holes (all paper numbers change).
- F3: AndroZoo key APPLIED by the user on 2026-10-15, waiting; without it, IzzyOnDroid first; Google Play downloads only
  with the supervisor's OK.
- F4a: whether callbacks join the flow definition or stay a separate hole type.
- Server builds for F1 and F4 start only when the user says so.

## Done (for reference)

Restructured paper (problem-first intro, real motivating example, background and definition, approach with theory,
6 RQs with answer boxes, comparative related work); TaintBench; budgeted checking; pricer panel; wording ablation; label
noise; GPT key; rubric relabeling (GPT done); FlowDroid with/without models on 80 apps; receipts on FlowDroid
(validation); Intent holes; conformal comparison on 324 apps; sensitivity and grouped splits; calibration floor;
figures from data.

LLMDFA (Wang et al., NeurIPS 2024, arXiv 2402.10754) verified and added on 2026-10-15: refs.bib, related.tex (next to IRIS and SemTaint), Related work.md.

## Next steps (agreed order, 2026-10-15)

Pipeline from here; times are working time unless marked as server time.

1. F1 finish (1-2 days). FlowDroid control running (`bench/queues/fd_fallback.sh`, up to about a day of server time):
   FlowDroid's out-of-memory apps get the bundled-library exclusion with only the time left after the memory cap
   (2100 s minus the seconds of the full run), exactly as our fallback; its timeouts used the whole budget and get no
   second run. The control reruns of FlowDroid's successful apps with sinks only measure leaks lost by the exclusion and
   are not counted as coverage. Then: paper text for the pipeline (approach, impl), RQ1 coverage and reach paragraph,
   same-budget paragraph in the Discussion, pipeline row in the main tables (main tables stay on the 307 apps), threats
   (R8-moved app code, fallback chosen after the 40-app subset, 27% undecidable library flows in the key). K2 for library
   disagreements skipped and disclosed.
2. Quick items (half a day): F5 recall-side headline; C2 from the F1 data (pricers on bundled-library methods: Jev holds,
   Sonnet misses AppCompatActivity.setContentView); C0 share of verdicts at Java-server source/sink entries.
3. B3 user value (about a day): false alarms per app before and after clearing, apps with no alarms left, receipt sizes.
4. F2 better pricers on a development subset (2-3 days; Sonnet variants possibly on the cloud-session credits, see
   `paper/CLOUD_CREDITS_PLAN.md`, expires 2026-11-05): Jev with the written definition (about $1-2 OpenRouter, needs
   approval) and free combinations of existing prices; no 5-sample Sonnet run (Claude Code usage).
5. F3 second population (about a week): AndroZoo when the key arrives; meanwhile prepare the IzzyOnDroid list (fixed in
   advance: date, size limit, seed). Build with the same pipeline (fallback included), labels via Claude Code and Codex,
   prices with approval.
6. Optional: F4 malware (a week or more); B2 kept as a validation, not pursued; C1 pinned pricer; C3 second rater.
7. Housekeeping D1-D7 last, when the numbers are final (1-2 days), then the authors' read-through.

Must-do total: about 4-6 working days plus server time; with F2 and F3: about 2.5-3.5 weeks; F4 adds about a week.

