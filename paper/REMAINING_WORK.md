# Remaining work (consolidated 2026-10-07, updated 2026-10-10)

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
- RUNNING since 2026-10-10: same-budget comparison (`bench/fd_budget.py`, results `data/fd_budget.jsonl`, log
  `data/fd_budget.log`): FlowDroid on all 585 picked F-Droid apps with our build's budget (2100 s, 16 GB per run; 2 runs of
  4 threads in parallel, like our build), with its models and with holes open (holes run skipped when the base run fails). Our outcome per
  app: 331 built, 253 over the limits (`data/android_failed.txt`). The 24 GB FlowDroid retry was stopped (superseded).
  Expect about 3 days. Then: one row/table in RQ1 and update the discussion paragraph.

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

## C. Further strengtheners (lower priority)

C0 (2026-10-08): FlowDroid's default source/sink list (2.15.1, which we use unchanged) contains Java server entries; some occur
in Android apps (`String.replace` as a sink, `File.getAbsoluteFile` as a source). The paper now states this (impl). Open:
measure the share of verdicts at such entries and, if large, add an Android-only sensitivity run (graph rebuild).

| # | Item | Why | Effort |
| --- | --- | --- | --- |
| C1 | Reproducible main pricer: report a pinned, rerunnable model next to Jev (Jev is a commercial service with an undisclosed model) | Verifiability criterion | days (pricing via Claude Code/Codex is free per call but not deterministic; an open-weight model run locally would be best, but the cheap open models we tried price too confidently) |
| C2 | Pricer on less-known code: hide bundled third-party libraries (OkHttp, Gson, Guava, Jsoup) or label them with StubDroid, and measure the pricer there | answers "the LLM memorized Android APIs" | about a week |
| C3 | Second human rater on ~20-40 facts for an agreement statistic (Cohen's kappa) | key quality | a few hours of a colleague's time |
| C4 | Transfer beyond F-Droid/TaintBench (e.g. AndroZoo or Play apps) | exchangeability across populations | build time; app access |
| C5 | Malware set larger than 31 apps for RQ6 | the transfer claim is weak on 31 apps | depends on available labeled malware |

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

## Done (for reference)
Restructured paper (problem-first intro, real motivating example, background and definition, approach with theory,
6 RQs with answer boxes, comparative related work); TaintBench; budgeted checking; pricer panel; wording ablation; label
noise; GPT key; rubric relabeling (GPT done); FlowDroid with/without models on 80 apps; receipts on FlowDroid
(validation); Intent holes; conformal comparison on 324 apps; sensitivity and grouped splits; calibration floor;
figures from data.
