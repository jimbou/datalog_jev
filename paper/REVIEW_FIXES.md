# Plan: three fixes for the reviewer weaknesses (written 2026-10-07)

Start these after the current work is done: Sonnet's rubric relabeling and `bench/queues/rk_chain.sh` (the main results
under the rubric key). Decide first which key is the paper's main key (recommended: the rubric key `rk-`), then run
everything below under that key. Rules from HANDOFF.md apply: no OpenRouter spending without asking (Jev is OpenRouter
only; it is cheap, ~$0.00002 per call, but ask), use Claude Code / Codex on the server for model calls.

Expected effect on acceptance (own estimate as a mock reviewer): about 25-30% now; with fix 1, 35-40%; with fixes 1, 3
and 4, about 45%.

---

## Fix 1. Remove the strawman: holes only where FlowDroid has no model

**STATUS: DONE (2026-10-08).** Evaluator prefix `fm-` (FlowDroid's models always taken from FlowDroid's labels); results in
`FINDINGS.md` section 22d; the paper now uses this setting as its main setting (rubric key). Headline: hard slice 5,318
leak-free sinks in 298 of 307 apps (old setting 20,104); 22,888 real leaks only through unmodeled methods; Jev clears 48.7%
at alpha 0.05 with 0.9% of apps wrong. New motivating example: `de.luhmer.owncloudnewsreader` (`ContentValues.put` real,
`TextToSpeech.setOnUtteranceProgressListener` not). TaintBench: only 6 documented leaks need unmodeled flows (all callbacks,
inter-component calls or reflection).

**Reviewer objection.** Our unsound analysis A0 has no library model at all: every framework call is a hole, including
the ~5,500 methods FlowDroid models (`String.equals`, `CharBuffer.toString`, ...). Part of the "hard slice" (28,335
leak-free sinks a sound analysis cannot clear) would be settled by FlowDroid's models. The motivating example uses two
FlowDroid-modeled methods and two `Log` sinks, which looks contrived.

**Goal.** A0' = our analysis plus FlowDroid's models. Modeled methods are code, not holes: their key-true flows become
code edges and their other candidate flows are removed. Only the methods FlowDroid does not model (12,274; source
`none`/`silver`/`rubric` in the hole file) stay holes and are priced. Report the main results for A0'.

**Implementation (mostly post-processing, no graph rebuild).**
1. `analysis/evaluate.py`: add a prefix mode `fm-` ("FlowDroid models fixed"), next to the existing `k1-`/`k1c-` code.
   The deletion mode already does half of this: with `k1`, modeled methods whose label is true become code edges
   (`fixed = modeled & ~gone & label True`). But it then keeps only the deleted modeled holes as candidates
   (`cu = cu[gone]`), dropping all unmodeled holes. For `fm-`: keep the modeled true flows as code edges, drop the
   modeled false flows, keep every unmodeled hole as a candidate. `MODELED` (the set of hole sources counted as
   modeled) already exists in `evaluate.py`. Combine with keys: `fm-rk-<pricer>`, or put `fm` first in the prefix loop.
   Truth for unmodeled holes comes from the chosen key; for modeled ones, FlowDroid's labels (same as the main key).
2. Server chain like `bench/queues/rk_chain.sh`: evaluate `fm-` for Jev, Sonnet, classifier (b6c, class folds), freq,
   uniform; `app_ltt.py` at alpha 0.05 and 0.1. Each evaluation is about 2 hours with `JOBS=5`.
3. Report: the new hard slice size (the sinks that depend only on unmodeled methods), how many verdicts A0 vs A0' gets
   wrong without any receipts (A0' misses only through unmodeled methods), cleared share and held-out wrong per pricer.
   Keep the old A0 numbers as a second setting ("no library model at all") only if space allows.
4. Budgeted checking (RQ5) and TaintBench (RQ6) under `fm-`: rerun `bench/queues/verify_chain.sh` style runs with
   `fm-choice-obj` and `taintbench_compare.py` on `fm-` results of the TaintBench graphs (`GRAPHS_DIR=data/graphs_tbl`).

**New motivating example.** Same idea as now (two verdicts in one app, one fact each, one real and one not), but:
- both facts must be on methods FlowDroid does **not** model (so FlowDroid itself would miss the leak);
- the sinks must be serious: network (`HttpURLConnection`, `OutputStream.write` on a socket), SMS (`sendTextMessage`),
  file writes, not `Log`.
How to find it: in the `fm-` results, select apps with a size-1 receipt that is real (high price) and a size-1 receipt
that is not (low price), both with source `silver`/`rubric`. Our result records do not store the sink API, so for each
candidate app extract its facts locally (as done for `org.jsl.wfwt`):
`java -Xmx4g -cp tools/soot-4.6.0-jar-with-dependencies.jar extract/Facts.java bench/apks/<apk> tools/android/android.jar "" <dir>`
then read `Call.facts`/`Arg.facts` for the sink site (`<method>/<index>` is the record's `site`). Prefer a fact whose truth
is also confirmed by K2 (StubDroid) or by the person's audit, so it does not rest on a language-model label only.

**Paper changes.** Introduction and abstract numbers; Section 2 example (new pair); Section 3 definition of A0 (A0 =
analysis with FlowDroid's models; holes = unmodeled methods); RQ1 (numbers); RQ2-RQ6 tables; the discussion paragraph about
FlowDroid. The tightness and certification theory is unchanged.

**Risk.** The hard slice shrinks and the cleared share may change in either direction (modeled facts were mostly cheap and
easy). The guarantee still holds. If the cleared share drops a lot, say so: the honest story is then "receipts for the
methods no model covers".

---

## Fix 3. Certify a threshold on FlowDroid itself

**Reviewer objection.** Our analysis reaches only 58% of FlowDroid's leaks with ~1% precision; "you certified the misses
of a toy analysis". Today, receipts inside FlowDroid are a validation (43 FlowDroid-confirmed receipts in 19 apps), not a
certified result, because too few apps have hole-dependent sinks.

**What exists.** `bench/fd_receipts.py` (FlowDroid with holes as summary files; base / holes-on / truth runs; receipts by
iterative cuts confirmed by reruns), `bench/fd_receipts_eval.py` (records for `app_ltt.py`), results in
`~/receipts/data/fd_receipts_{fdroid,tb}/`. On 181 small F-Droid apps, 87 failed, 58 of them because FlowDroid's own
plain run exceeded `FD_TIMEOUT=1200` s.

**Steps.**
1. More time: rerun the failed apps with `FD_TIMEOUT=3300` (the FlowDroid validation used 3300 s and `-dt 2400`). Only
   the failed ones: the script skips apps that already have an output JSON, so move the `failed` JSONs aside first.
2. More apps: we need on the order of 60+ apps *with hole-dependent sinks* to certify alpha 0.1 comfortably (the floor
   for alpha 0.1, eps 0.1 is 22 calibration apps with zero failures; half splits double that). Today about 1 in 6
   completed apps has any. So aim for ~400 more completed small apps: download more small F-Droid APKs (the corpus
   list in `bench/apks/pick*.txt`; `bench/flowdroid_select.py` picks from APKs that our evaluation covers, so add a
   variant that does not require our graphs), and include TaintBench and similar small malware sets.
3. Tighter receipts: today a call written against an app class (`this.getSystemService`) is mapped to every unmodeled
   framework method with that sub-signature, which inflates bounds. Resolve the real framework class from the app's
   class hierarchy (the `Super`/`Class` facts from `extract/Facts.java`) and map only to the methods it inherits.
4. Decide and state the unit: apps without any hole-dependent sink have loss 0 at every threshold. Including them in
   calibration is valid under the definition (risk over all programs) but makes the guarantee easier; report both
   "all apps" and "apps with at least one hole-dependent sink".
5. Calibrate (`app_ltt.py fdr-<pricer>` after `fd_receipts_eval.py`), alpha 0.1 and, if enough apps, 0.05.
6. Paper: add a row or short table to RQ2 ("FlowDroid with receipts: cleared share, held-out apps wrong, apps"), and
   rewrite the discussion paragraph from "validation" to "certified on FlowDroid".

**Cost.** Server days (FlowDroid is slow: holes-on runs and the iterative cut reruns multiply the time per app). No
model calls except pricing new library methods (Sonnet via Claude Code; Jev only with approval).

**Risk.** Even with more apps, holes may add few sinks per FlowDroid run (its source/sink list is narrow on small apps).
If certification stays out of reach, keep it as validation and say so.

---

## Fix 4. Show what it buys a user

**Reviewer objection.** "40% of the hard slice" is abstract; no user, no saved effort.

**Measure (post-processing on existing results, about a day).**
1. Alarms per app. For each app, the alarms a sound analysis reports that are not real (leak-free hole-dependent
   sinks) and how many remain after certified clearing. Report median and distribution per app (a small figure: per-app
   alarms before / after), and the number of apps whose false-alarm list becomes empty.
   Source: `data/android_<pricing>.jsonl` (`truth_lo` false and `bound` not None = false alarm of the sound analysis;
   cleared if `bound <= delta`, with delta the threshold certified on all apps, e.g. via `paper_stats.py`).
2. Triage effort. Translate into inspection effort with an explicit, cited or measured cost per alarm (do not invent one:
   either measure it on a small sample, e.g. the person times the review of 20 alarms using receipts vs without, or report
   alarms only). Receipts also shorten each inspection: an alarm with a one-fact receipt is reviewed by checking one fact.
   Report the receipt size of the remaining alarms.
3. Shared checks across apps. From RQ5: how many apps' reports change when one fact is checked (e.g. `Messenger.send`
   unlocks 481 verdicts in 85 apps); per-app effort of checking the top 25 facts once for the whole corpus.
4. Optional small user study (strong but costs people's time): 2-3 people triage the alarms of 5 apps with and without
   receipts; measure time and decisions. Only if a colleague is available.

**Paper changes.** A paragraph and a figure in RQ2 or a new short RQ ("What does clearing save an analyst?"), and one
sentence in the introduction's results paragraph.

---

## Order and checklist
1. Wait for `RK-DONE`; choose the main key.
2. Fix 1 (evaluate `fm-` mode, chain, new example, paper numbers).
3. Fix 4 (post-processing on the fix-1 results).
4. Fix 3 (server days; can run in the background while 1 and 4 are written up).
5. Re-run `paper/make_figs.py` and `analysis/paper_stats.py` for the new results; update tables; check page budget
   (body must end by page 18).
