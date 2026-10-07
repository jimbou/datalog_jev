# Handoff: Soundiness with Receipts (as of 2026-10-07, evening UTC)

Paper: "Soundiness with Receipts: Certified Miss-Risk for Unsound Static Analyses", target ISSTA 2027 (the call we
followed was ISSTA 2026's: acmsmall, 18 pages without references and Data Availability, double-anonymous, AI disclosure
required; check the 2027 call when it is out). Repository: `/home/jim/datalog_jev` (laptop) and `~/receipts` (server).
No secrets in this file.

Read first: this file, `FINDINGS.md` (research log, newest sections 22, 22b), `paper/PLAN.md` (claims, evidence, status),
`~/server_connect_pku.md` (how to reach the server). Memory notes for the agent live in
`~/.claude/projects/-home-jim-datalog-jev/memory/`.

## 1. The idea in one paragraph
Unsound taint analyses skip library code and assume no data flows through it. Every candidate flow through a skipped
library method is a *hole*. For each clean verdict a min-cut gives its *receipt* (the cheapest set of assumed-absent
flows it rests on); a *pricer* (an LLM) prices each flow; the receipt's price bounds the probability the verdict is wrong
(tightest bound from marginals, no independence needed). A threshold on that bound is certified per program with
Learn-then-Test (exact binomial, fixed sequence), which makes the analysis "(alpha, eps)-soundy" (Definition in the paper).

## 2. Where the results stand (numbers the paper uses)
Main corpus: 332 F-Droid graphs, 324 apps with hole-dependent verdicts, 84,753 such sinks, 28,335 leak-free (main key).

| Result | Value |
| --- | --- |
| Sound over-approximation clears | 72.0% of leak-free sinks |
| Jev, main key, alpha 0.05 | 40.0% of the hard slice cleared, 1.0% held-out apps wrong |
| Sonnet 5 (verbalized), main key | 29.6% (2.5%) at 0.05; 53.0% at 0.10 |
| Counting (no prices) | 0% at any alpha; receipts of size one wrong in 93% of apps |
| Verdict-level conformal (FDR 5%) | 55.6% cleared but 166/324 apps (51%) with a wrong clearance |
| Calibration floor | certifiable only if (1-alpha)^n <= eps; confirmed empirically (n = 40/60/120 for alpha .1/.05/.02) |
| Budgeted checking (main key) | 25 checked facts: 53.2%; 100 by count: 64.2%; 400: 66.2%; 100 random: 40.0% (no gain) |
| Budgeted checking (K2 key) | 0 -> 25.5%, 50 facts -> 78.7%, 200 -> 83.5% |
| TaintBench (malware, 33 apps) | 48 of 92 reached documented leaks need library holes; F-Droid threshold transfers (Jev 0/31 apps wrong) |
| FlowDroid without its library model | loses 127 of 154 leaking sinks (82%) on 69 apps |
| Our analysis vs FlowDroid (80 apps) | reaches 58% of FlowDroid's leaks, ~1% precision (the main weakness) |
| Pricer panel (5 cheap LLMs) | price too confidently: certify little or nothing; validity always held |
| Wording ablation (Jev) | object convention 40.0% vs "choice" 14.2% vs "taint" 25.4% (alpha 0.05) |
| GPT key (loose prompt) | Jev 22.9% (1.8%), Sonnet 24.0% (0.9%) at 0.05 |
| Label noise (11% of "no" flipped, 3 seeds) | validity holds; Jev 7.6-13.9%, Sonnet 17.0-23.1% |
| Rubric relabeling (written definition) | Sonnet vs GPT kappa 0.62 -> 0.80; both 93% agreement with the person's source checks |
| Inter-component (Intent) holes | work (receipts mix both hole kinds, alpha 0.1: Jev 40.2%, 1.4% wrong on 72 apps); no extra TaintBench leaks |
| Receipts on FlowDroid itself | 120 apps finished; holes add 58 sinks in 19 apps, 43 confirmed receipts; too few to calibrate (validation only) |
| Library-model case study | null: ranking FlowDroid's next summaries by receipts does not beat frequency or random (not a paper claim) |

Honest assessment given to the user: a borderline ISSTA submission (roughly 1 in 3); main risks are the weak analysis
(58% recall vs FlowDroid) and key/pricer entanglement. The rubric key is the planned answer to the second.

## 3. Running right now (server)
1. **Sonnet rubric relabeling** (`PROMPT=rubric BACKEND=claude probes/run_oracle.py ... rubric-sonnet5`, 4 threads; 12
   threads hit Claude Code rate limits). Output `data/oracle-rubric-sonnet5.jsonl`; at ~9,200 of 12,362 methods on
   2026-10-07 19:50 UTC, ~20/min. GPT's (`oracle-rubric-gpt61.jsonl`) is complete.
2. **`bench/queues/rk_chain.sh`** waits for (1), then evaluates ten pricers under the rubric key `rk-` (Jev and Sonnet
   first, ~1.5 h each) and runs LTT at alpha 0.05 and 0.1. Log: `data/rk_chain.log` (`END rk-<pricer>`, `RK-DONE`).
   Results: `data/ltt_rk-<pricer>_a05.log` / `_a1.log`.

Check: `ssh pku 'cd ~/receipts/data; wc -l < oracle-rubric-sonnet5.jsonl; cat rk_chain.log'`.

## 4. Next steps, in order
1. When `RK-DONE`: fill the placeholder table `tab:rubric` in `paper/sections/results.tex` (main results under the rubric
   key next to the main key). Decide with the user whether the rubric key becomes the main key of the paper (recommended:
   yes, it follows the written definition; then the headline numbers, Table 2, the deletion text and budgeted checking must
   be rerun/updated under `rk-`: deletion uses FlowDroid models and is unaffected; budgeted checking needs
   `VERIFY_FILE` runs with `rk-choice-obj`).
2. Recompute Sonnet-rubric accuracy on all 60 human facts (now 41/44) and the final agreement (script in the 2026-10-07
   transcript; easy to rewrite: map human rows to atoms via `holes_android_fw.jsonl`, compare labels).
3. Paper is at the 18-page limit (Data Availability starts on p. 18): trim. Candidates: per-app tables to the appendix,
   shorten RQ6 cost, merge the case study out (it is null and not in the paper), shorten Intent holes to a paragraph
   (not yet in the paper at all; FINDINGS 22b has the numbers).
4. Remaining placeholders: pipeline figure (TikZ), `tab:facts`, `tab:cost`, `tab:corpus`, `tab:audit`, `tab:rubric`,
   appendix proof details, anonymous artifact link and AI-tool names (Data Availability, AI disclosure).
5. Optional strengtheners: second human rater (kappa) on ~20 facts; FlowDroid receipts with longer timeouts (most F-Droid
   failures were FlowDroid's own 20-minute limit).

## 5. Rules the user set (also in agent memory)
- **Do not spend OpenRouter credit.** Use Claude Code (`BACKEND=claude`) and Codex (`BACKEND=codex`) on the server
  (`probes/cli_llm.py`). Jev exists only on OpenRouter: ask before any Jev call, with the expected cost (it is ~$0.00002 per
  call). Total OpenRouter spend so far: Sonnet pricing ~$16.4, panel ~$10.5, small extras.
- Be strict and honest about results; the user explicitly asked not to be pleased.
- Explain plainly; the user likes status tables and short summaries.
- The CLI logins on the server expire: Claude Code login via tmux (`claude auth login`, paste the code the user gets);
  Codex via `codex login --device-auth` in tmux (user opens auth.openai.com/codex/device and enters the code).

## 6. Code map (what was added in this stretch)
- `analysis/evaluate.py`: per-app min-cut evaluation. Keys by pricing prefix: `k2-`, `k2s-`, `au-`, `ah-`, `ah2-`, `gk-`
  (GPT loose), `rk-` (rubric), `kn<seed>-` (label noise), `k1-`/`k1c-` (deletion). Env: `GRAPHS_DIR`, `OUT_SUFFIX`, `JOBS`,
  `VERIFY_FILE` (budgeted checking), `ICC_PRICES`/`ICC_DEFAULT` (Intent holes). Missing prices fall back to 0.5.
- `analysis/app_ltt.py` (calibration), `analysis/sensitivity.py`, `analysis/conformal.py` (now reports apps with a wrong
  clearance), `analysis/paper_stats.py` + `paper/make_figs.py` (figures as pgfplots), `analysis/k1_summary.py` (now reports
  the share of splits above alpha, the quantity the guarantee bounds), `analysis/verify_select.py` + `verify_summary.py`
  (budgeted checking), `analysis/taintbench_compare.py`, `analysis/make_taint_icc.py` -> `taint_icc.dl` (Intent holes).
- `probes/run_oracle.py` (key labels; `PROMPT=rubric`, `BACKEND`, `ORACLE_THREADS`), `probes/run_sonnet_price.py`
  (verbalized pricer; `BACKEND`, `PRICE_THREADS`, `NO_REASONING`), `probes/cli_llm.py`, `probes/price_icc.py`,
  `probes/make_summaries.py` (FlowDroid summaries for the case study), `probes/extend_holes_fw.py` (`GRAPHS_DIRS`).
- `extract/Facts.java` now records class constants (`cls:`), `extract/Manifest.java` dumps manifest components.
- `analysis/run_android.py` env: `SOURCES_SINKS`, `APK_LIST`, `FROM_APK`, `TAINT_DL`, plus the older ones.
- `bench/fd_receipts.py` + `fd_receipts_eval.py` (receipts on FlowDroid), `bench/flowdroid_cs.sh` + `cs_compare.py`
  (case study), `bench/queues/*.sh` (every server chain of this stretch; force-added, `bench/` is git-ignored).
- Paper: `paper/main.tex` + `paper/sections/*.tex`, figures in `paper/figs/`; build with `latexmk -pdf main.tex`.

## 7. Server data (in `~/receipts/data`)
Graphs: `graphs/` (332, main), `graphs_tb`/`graphs_tbl` (TaintBench, default/TB list), `graphs_icc80c`, `graphs_icc_tblc`,
`graphs_icc_tbc` (Intent holes). Results: `android_<pricing>[_suffix].jsonl`. Prices: `jev_holes_android_fw_<tag>_r0.jsonl`
(tags: choice-obj = Jev main, taint, choice, sonnetp, q27, qflash, dsflash, gflash, luna). Labels: `oracle-sonnet5-unk`,
`oracle-gpt61-unk`, `oracle-rubric-{sonnet5,gpt61}`. FlowDroid: `flowdroid/`, `flowdroid_none/`, `flowdroid_cs/`,
`fd_receipts_{fdroid,tb}/`. Chain logs: `*_chain.log`.

## 8. Gotchas
- `pkill -f PATTERN` matches its own ssh command line if the pattern text appears unbracketed anywhere in the same remote
  command (this killed a session once): kill by PID, or keep the restart in a separate ssh call.
- The local dcg hook blocks redirects to variable paths and `rm -rf`: write scripts with literal paths, use fresh dirs.
- VPN drops make `ssh pku` fail ("No route to host"): ask the user to reconnect; server jobs keep running.
- Monitors expire every 30 minutes; re-arm them, and make the loop skip empty ssh results.
