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
