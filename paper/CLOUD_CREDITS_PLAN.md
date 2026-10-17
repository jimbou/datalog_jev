# Using the Claude Code cloud-session credits for F2's Sonnet pricers (plan, 2026-10-15; not tried yet)

## The credit

The user's account has "Cloud session credits": an included credit that applies automatically to Claude Code cloud
sessions (claude.ai/code, remote sessions) and **expires 2026-11-05 09:59 GMT+2**. After it is used or expires, the plan's
regular usage applies. Balance: not known yet (check on claude.ai before starting).

## Why it matters

F2 (REMAINING_WORK.md) wants Sonnet 5 pricers. Our Sonnet pricing so far ran `claude -p` on the PKU server
(`probes/run_sonnet_price.py`, `BACKEND=claude`), which draws on the plan's regular usage, not on these credits.
Measured on 2026-10-15: one pricing call is about $0.009 in API-equivalent usage (methods with 1 to 9 candidate flows;
library methods cost more).

| Variant | Calls | Equivalent usage | Time at 8 threads |
| --- | --- | --- | --- |
| Sonnet, 1 sample, dev subset (92 apps, about 5,300 methods) | about 5,300 | about $50 | about 4 h |
| Sonnet, 5 samples, dev subset | about 26,500 | about $240 | about 18 h |
| Sonnet, 5 samples, main + rescued (17,894 methods) | about 89,000 | about $800 | about 60 h |

## Two ways to use the credit

1. **Our script inside a cloud session.** The session clones the repository from GitHub and runs
   `run_sonnet_price.py` (or `run_oracle.py`) with `BACKEND=claude`, unchanged: the same pricer, comparable results.
   Unknown: whether `claude -p` inside the cloud machine is logged in and billed to the credit rather than to the plan.
2. **The cloud agent prices the methods itself, in batches.** Certainly billed to the credit, but a different pricer
   (other context, batch answers, less reproducible): report it as its own F2 variant (the guarantee holds for any
   pricer, Proposition 2).

## Steps when we try it

1. Push the repository (the hole file, prices and rubric labels are in commits not yet pushed as of 2026-10-15).
2. Note the credit balance and the plan's usage on claude.ai.
3. Start one cloud session (claude.ai/code, or a remote agent from the CLI) that prices about 30 dev-subset methods with
   way 1, writing to a new tag (e.g. `sonnetcloud`), and commits the output file to a branch.
4. Check on claude.ai that the credit went down and the plan's usage did not. Compare the 30 prices with the server's
   `sonnetp` prices for the same methods.
5. If way 1 is billed to the credit: run F2's Sonnet variants there (dev subset first, seeded 30% draw fixed before any
   run), in chunks that finish well before 2026-11-05. If not: way 2 as an extra variant, or skip Sonnet in F2.

## Budget for F2 on the credit (about $249 left, about $0.01 per call)

Sonnet with 3 samples per method (price = the highest): dev subset 5,094 methods = 15,282 calls (about $150); if it is
chosen on the dev subset, the other main apps need 7,518 - 5,094 = 2,424 methods = 7,272 calls (about $75). Total about
$225, inside the credit. 5 samples on the dev subset alone (about $255) would not fit. The rescued apps' 10,000+ new
methods would need the plan's usage or another source.

## Constraints

- The cloud session only sees what is on GitHub; keep keys out (no OpenRouter calls from the cloud; Jev stays on the
  server with the user's approval).
- Fix the dev subset (seed, 30% of the 307 main apps) before pricing, and list every variant tried (F2 rules).
- Record the model id and CLI version the cloud session used.

## Attempt log

- 2026-10-16: a "remote" agent started from the CLI ran on the laptop instead (remote agents are not available in this
  setup); it stopped before any call because the laptop's Claude Code has ANTHROPIC_API_KEY set (local `claude -p` would
  bill that key, and says nothing about the cloud credit). No routines exist on the account. Next: start the session by
  hand on claude.ai/code with the prompt below.
- 2026-10-16: private repository not accessible from claude.ai/code ("Authentication failed"); the user made it public.
- 2026-10-16, cloud session on claude.ai/code (hostname `vm`, claude 2.1.301 at /opt/node22/bin/claude, Python 3.13.16; no
  ANTHROPIC_API_KEY / CLAUDE_CODE_OAUTH_TOKEN / ANTHROPIC_AUTH_TOKEN set): `claude -p` WORKS (test call
  total_cost_usd 0.0104, model claude-sonnet-5). Way 1 priced all 30 methods unchanged, 0 errors, 57 s at 4 threads.
  Against the server's sonnetp prices (30/30 methods, 107 atoms): mean absolute difference 0.067, both <= 0.05 for
  61.7% of atoms, differ by more than 0.3 for 7.5% (8 atoms). Credit 250 -> 249 (whole session). Results NOT pushed:
  git push 403 and the GitHub connector "Resource not accessible by personal access token": the session can read the
  repository but not write. Fix before a full run: reconnect GitHub at https://claude.ai/connect-github (Claude GitHub
  App with write access to jimbou/datalog_jev).

## Prompt for the cloud session (claude.ai/code, repository jimbou/datalog_jev, branch main)

Small test of whether `claude -p` works in this cloud session, pricing 30 methods (paper/CLOUD_CREDITS_PLAN.md, way 1,
then way 2 only if way 1 fails). No OpenRouter or other paid API calls; do not install or log in to anything; never print
secret values.
1. Record: `hostname`, `which claude`, `claude --version`, `python3 --version`, which of ANTHROPIC_API_KEY,
   CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_AUTH_TOKEN are set (names only), and whether
   `claude -p "Say ok." --model claude-sonnet-5 --tools "" --max-turns 1 --output-format json` works (print only
   is_error, result, total_cost_usd, model ids). If the hostname looks like a personal laptop, stop and report.
2. Way 1: `cd probes && BACKEND=claude PRICE_THREADS=4 python3 run_sonnet_price.py claude-sonnet-5 sonnetcloud f2_test30`
   (writes data/jev_f2_test30_sonnetcloud_r0.jsonl; rerun once if some methods fail).
3. Way 2 only if `claude -p` does not work: price the 30 records of data/f2_test30.jsonl yourself with the SYSTEM prompt
   and the question text of ask1() in probes/run_sonnet_price.py (state/endpoint from probes/run_jev.py), one method at a
   time, into data/jev_f2_test30_sonnetagent_r0.jsonl (same format, cost 0).
4. Compare with data/jev_holes_android_fw_sonnetp_r0.jsonl (match cls+sig): methods and atoms matched, mean absolute
   difference, share of atoms both <= 0.05, share differing by more than 0.3.
5. Write data/f2/cloud_test_report.md (time, step-1 facts, way used, priced/errors, wall-clock, costs seen, comparison).
6. Branch cloud-test-20261016: commit only the report and the new price file (`git add -f`), push the branch. Never push
   to main, never force-push.

## F2 run prompt (dev subset, Sonnet 5.5, 3 samples, cap $150)

Session model in the claude.ai/code picker: Sonnet 5.5 (the session only starts and watches a script; the pricing
model is set in the command). Paste:

F2 pricing run for paper/CLOUD_CREDITS_PLAN.md. Do only this; no other changes, no paid APIs, no installs, never push
to main, never force-push.
1. From the repository root start, in the background:
   `nohup bash bench/cloud_price.sh claude-sonnet-5-5 sonnet55def3 f2_dev 3 150 f2-cloud-sonnet55 250 6 > /tmp/cloud_price.log 2>&1 &`
   It prices data/f2_dev.jsonl (5,094 methods) with `claude -p`, 3 samples per method under the written flow definition,
   pushes data/jev_f2_dev_sonnet55def3_r0.jsonl to branch f2-cloud-sonnet55 after every 250 methods, and stops at $150
   API-equivalent. If the branch already exists it resumes from it.
2. Every 9 minutes (one `sleep 540; tail -n 3 /tmp/cloud_price.log` per check, nothing else) report the last CHUNK line.
   If the log shows errors for most methods or "PUSH FAILED" twice in a row, stop the job (kill its PID) and report.
3. When the log says DONE or CAP reached, report the final line, the number of priced methods and the cost, and confirm
   the last push succeeded (`git log origin/f2-cloud-sonnet55 -1`).

## Follow-up prompt (after the 5,094 dev methods are done): the rest of the main corpus, cap $40

Same session (or a new one on branch main). Paste:

Next pricing job for paper/CLOUD_CREDITS_PLAN.md. Same rules: only this; no paid APIs, no installs, never push to main,
never force-push.
1. Make sure the dev job has ended (its log says DONE or CAP reached) and its last chunk is on origin
   (`git log origin/f2-cloud-sonnet55 -1`).
2. Bring the new dataset from main into the results branch and push it:
   `git fetch origin main f2-cloud-sonnet55 && git checkout -B f2-cloud-sonnet55 origin/f2-cloud-sonnet55 && git merge --no-edit origin/main && git push origin f2-cloud-sonnet55`
   (data/f2_rest.jsonl, 2,424 methods: the main corpus's unmodeled methods outside the dev subset).
3. Start in the background:
   `nohup bash bench/cloud_price.sh claude-sonnet-5-5 sonnet55def3 f2_rest 3 40 f2-cloud-sonnet55 250 6 > /tmp/cloud_price_rest.log 2>&1 &`
   It writes data/jev_f2_rest_sonnet55def3_r0.jsonl and pushes it to the same branch after every 250 methods; it stops at
   $40 API-equivalent for this file.
4. Every 9 minutes (`sleep 540; tail -n 3 /tmp/cloud_price_rest.log`) report the last CHUNK line; stop the job if most
   methods error or "PUSH FAILED" appears twice in a row. At the end report the final line and confirm the last push.

## G4 prompt (IzzyOnDroid labels and prices; caps $60 + $45 + $15)

`data/f3_izzy.jsonl` was pushed to main on 2026-10-16 (2f756fe): 2,648 methods, 23,978 candidate flows (about 9 per
method: mostly bundled-library methods), from 94 of the 134 IzzyOnDroid apps (68 full builds, 26 fallback). Credit:
about $180 left (expires 2026-11-05 09:59 GMT+2). Order by need: (1) Sonnet 5 rubric labels (the answer key; without them
no evaluation), (2) sonnet55def3, the pricer F2 picked on the dev subset (max(Jev, sonnet55def3)), estimated $35 from the
dev cost model $0.0069 + $0.00068 per candidate flow, (3) sonnetp (Sonnet 5 baseline, 1 sample, short question). Paste
into a claude.ai/code session on repository jimbou/datalog_jev, branch main, session model Sonnet 5.5:

> IzzyOnDroid labeling and pricing job for paper/REMAINING_WORK.md (G4) and paper/CLOUD_CREDITS_PLAN.md ("G4 prompt"). Do only this; no
> paid APIs, no installs, never push to main, never force-push, never print secret values.
> 1. `git fetch origin main && git checkout -B f3-cloud-izzy origin/main && wc -l data/f3_izzy.jsonl` (expect 2648; stop
>    and report if the file is missing).
> 2. Answer-key labels first. Start in the background:
>    `KIND=label nohup bash bench/cloud_price.sh claude-sonnet-5 rubric-sonnet5-izzy f3_izzy 1 60 f3-cloud-izzy 250 6 > /tmp/cloud_label.log 2>&1 &`
>    It writes data/oracle-rubric-sonnet5-izzy.jsonl with the written flow definition (reason codes), pushes it to branch
>    f3-cloud-izzy after every 250 methods, and stops at $60 API-equivalent.
> 3. Every 9 minutes (`sleep 540; tail -n 3 /tmp/cloud_label.log`, nothing else) report the last CHUNK line. Stop the job
>    (kill its PID) and report if most methods error or "PUSH FAILED" appears twice in a row.
> 4. When the log says DONE or CAP reached, start the Sonnet 5.5 prices on the same branch:
>    `nohup bash bench/cloud_price.sh claude-sonnet-5-5 sonnet55def3 f3_izzy 3 45 f3-cloud-izzy 250 6 > /tmp/cloud_s55.log 2>&1 &`
>    (writes data/jev_f3_izzy_sonnet55def3_r0.jsonl: written definition, 3 samples, cap $45), and monitor it the same way.
> 5. When that ends, the Sonnet 5 prices:
>    `PRICE_PROMPT=short nohup bash bench/cloud_price.sh claude-sonnet-5 sonnetp f3_izzy 1 15 f3-cloud-izzy 250 6 > /tmp/cloud_sonnetp.log 2>&1 &`
>    (writes data/jev_f3_izzy_sonnetp_r0.jsonl, 1 sample, cap $15), monitored the same way.
> 6. At the end report the three final lines (methods, cost), the `claude --version`, and confirm the last push
>    (`git log origin/f3-cloud-izzy -1`).

## Last-credit prompt (about $20 left, 2026-10-17): third labeler on the audited facts, then rescued-app prices

(1) Sonnet 5.5 rubric labels (written definition, reason codes) for the 314 methods behind the key's 446 audited facts
(`data/audit_methods.jsonl`, 1,572 candidate flows): a third labeler to compare with the key and with the person's
source checks (key quality, next to G2). (2) With what is left, Sonnet 5.5 prices (1 sample; one sample is as good as
three on the dev subset) for the smallest 3,524 of the 10,376 unpriced methods of the F1-rescued apps
(`data/f1_s55_cloud.jsonl`); the server prices the other 6,852 with Claude Code (`data/f1_s55_server.jsonl`). Paste into a
claude.ai/code session on repository jimbou/datalog_jev, branch main, session model Sonnet 5.5:

> Last credit job for paper/CLOUD_CREDITS_PLAN.md ("Last-credit prompt"). Do only this; no paid APIs, no installs, never
> push to main, never force-push, never print secret values.
> 1. `git fetch origin main && git checkout -B last-cloud origin/main && wc -l data/audit_methods.jsonl data/f1_s55_cloud.jsonl`
>    (expect 314 and 3524; stop and report if missing).
> 2. Start in the background:
>    `KIND=label nohup bash bench/cloud_price.sh claude-sonnet-5-5 rubric-sonnet55-audit audit_methods 1 10 last-cloud 50 4 > /tmp/cloud_audit.log 2>&1 &`
>    (writes data/oracle-rubric-sonnet55-audit.jsonl, pushes to branch last-cloud every 50 methods, cap $10).
> 3. Every 9 minutes (`sleep 540; tail -n 3 /tmp/cloud_audit.log`, nothing else) report the last CHUNK line; stop the job
>    and report if most methods error or "PUSH FAILED" appears twice in a row.
> 4. When it says DONE or CAP reached, start on the same branch:
>    `nohup bash bench/cloud_price.sh claude-sonnet-5-5 sonnet55def1 f1_s55_cloud 1 9 last-cloud 250 6 > /tmp/cloud_f1.log 2>&1 &`
>    (writes data/jev_f1_s55_cloud_sonnet55def1_r0.jsonl, 1 sample, cap $9), monitored the same way. If the credit runs
>    out first, just report how far it got; the pushed file is enough.
> 5. At the end report both final lines and confirm the last push (`git log origin/last-cloud -1`).
