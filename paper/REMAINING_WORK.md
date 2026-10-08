# Remaining work (consolidated 2026-10-07, updated 2026-10-08)

This file replaces the open items in `paper/PLAN.md` (now historical), the "next steps" in `FINDINGS.md` §23 (stale:
conformal selection, key labels, a second hole type and the Praline check are done) and summarizes
`paper/REVIEW_FIXES.md` (details for items B1-B3). Status of the paper: restructured in the lab's style (commit 757bf0d),
body ends on page 16 of 18, compiles without errors or overfull lines.

Mock-review estimate of acceptance: about 35-40% now (B1 done, rubric key as main key); about 45% with B2-B3; other items add less.

**Main setting since 2026-10-08:** FlowDroid's models as code (evaluator prefix `fm-`), rubric key as main key (`fm-rk-<pricer>`).

## A. Finish what is running (must do)

A1-A5 are done (rubric relabeling, rubric key as main key, agreement numbers). Still open: the remaining `fm-` runs
(`bench/queues/fm_all_chain.sh`: other keys, pricer panel, wording, ablation, figure statistics) and filling RQ3/RQ4 and the
figures with them.

| # | Item | Status / how |
| --- | --- | --- |
| A1 | Sonnet rubric relabeling | running on the server (`data/oracle-rubric-sonnet5.jsonl`, ~10,000 of 12,362 on 2026-10-07 20:30 UTC) |
| A2 | Main results under the rubric key | `bench/queues/rk_chain.sh` starts after A1; `data/rk_chain.log`, `ltt_rk-*` |
| A3 | Fill the rubric row of Table 4 (`tab:keys`) and check the RQ3 box ("all eight keys") | after A2 |
| A4 | Final Sonnet-rubric accuracy on all 60 person-checked facts and final agreement numbers | after A1; update RQ3 text (now "93%, kappa 0.80" from partial data) |
| A5 | Decide the paper's main key (recommended: rubric key) and, if switched, rerun the main tables, budgeted checking and TaintBench under it | decision for the user, then reruns |

## B. Acceptance improvers from the mock review (see `REVIEW_FIXES.md`)
| # | Item | Why | Effort |
| --- | --- | --- | --- |
| B1 | DONE 2026-10-08: holes only where FlowDroid has no model (`fm-` mode), new example (`ContentResolver.insert` leak through unmodeled `ContentValues.put`) | removed the strawman objection | done |
| B2 | Certify on FlowDroid itself: rerun failed apps with 3300 s, ~400 more small apps, tighter class mapping | removes "certified misses of a toy analysis" | server days; may stay a validation |
| B3 | Show user value: false alarms per app before/after clearing, apps with no alarms left, receipt size of remaining alarms, shared checks across apps; optional timed triage sample | makes "40% of the hard slice" concrete | about a day; user study optional |

## C. Further strengtheners (lower priority)

New (2026-10-08): FlowDroid's default source/sink list (2.15.1, which we use unchanged) contains Java server entries; some occur
in Android apps (`String.replace` as a sink, `File.getAbsoluteFile` as a source). Measure the share of verdicts at such
entries and, if large, add an Android-only sensitivity run (needs a graph rebuild with a filtered list).

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
- Main key (A5).
- Whether to do B2 (server days, uncertain outcome) and C1/C2 (time).
- Whether a colleague can be the second rater (C3) or join a small triage study (B3 optional).
- Target venue/date (ISSTA 2027 deadline unknown until the call is out).

## Done (for reference)
Restructured paper (problem-first intro, real motivating example, background and definition, approach with theory,
6 RQs with answer boxes, comparative related work); TaintBench; budgeted checking; pricer panel; wording ablation; label
noise; GPT key; rubric relabeling (GPT done); FlowDroid with/without models on 80 apps; receipts on FlowDroid
(validation); Intent holes; conformal comparison on 324 apps; sensitivity and grouped splits; calibration floor;
figures from data.
