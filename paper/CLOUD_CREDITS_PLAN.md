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

## Constraints

- The cloud session only sees what is on GitHub; keep keys out (no OpenRouter calls from the cloud; Jev stays on the
  server with the user's approval).
- Fix the dev subset (seed, 30% of the 307 main apps) before pricing, and list every variant tried (F2 rules).
- Record the model id and CLI version the cloud session used.
