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
- d. RUNNING since 2026-10-13 04:18 (restarted 06:11 with the fix): 253 failed apps. At 49: 3 built (one by the fix, one
  by the longer time), all others out of memory, so memory is the bottleneck.
- e. Subset DONE (`data/f1e_subset.tsv`, 20 built + 20 failed, seed 20261013; prefixes `data/bundled_libs.txt`, fixed
  before results). Built apps: sources 181 -> 68, sinks 923 -> 441, hole-dependent sinks 5,490 -> 1,317 (most sources and
  sinks sit inside bundled libraries; in 4 apps all sources go): rejected for all apps. Failed apps: 8 of 20 build, and all
  8 run out of memory without step e (attribution run, `data/f1/reasons_attrib.tsv`). Minified apps (e.g. app.devswitch,
  96% renamed classes) gain little from prefixes.
- e as fallback: QUEUED after d (`bench/queues/f1e_fallback.sh`): every app still failing on memory or time gets step e
  with only the time its full attempt left (2100 s minus its recorded seconds), 16 GB, so the per-app budget stays
  FlowDroid's. Then decide whether rescued apps enter the corpus (needs rubric labels via CLIs, K2 labels, Jev prices
  with approval) and describe the mixed corpus.

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
- F3: request an AndroZoo API key; without it, IzzyOnDroid first; Google Play downloads only with the supervisor's OK.
- F4a: whether callbacks join the flow definition or stay a separate hole type.
- Server builds for F1 and F4 start only when the user says so.

## Done (for reference)
Restructured paper (problem-first intro, real motivating example, background and definition, approach with theory,
6 RQs with answer boxes, comparative related work); TaintBench; budgeted checking; pricer panel; wording ablation; label
noise; GPT key; rubric relabeling (GPT done); FlowDroid with/without models on 80 apps; receipts on FlowDroid
(validation); Intent holes; conformal comparison on 324 apps; sensitivity and grouped splits; calibration floor;
figures from data.
