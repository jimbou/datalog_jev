# Cloud session test: `claude -p` pricing of 30 methods (2026-10-16)

Run at 2026-10-16 02:29 UTC in a Claude Code cloud session (claude.ai/code), repository jimbou/datalog_jev.

## Step 1: environment

- hostname: `vm` (cloud container, not a laptop)
- `which claude`: /opt/node22/bin/claude; `claude --version`: 2.1.301 (Claude Code)
- `python3 --version`: Python 3.13.16
- ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_AUTH_TOKEN: all unset in the shell
- `claude -p "Say ok." --model claude-sonnet-5 --tools "" --max-turns 1 --output-format json`: works;
  is_error=false, result="Ok.", total_cost_usd=0.010363, model ids: claude-sonnet-5

## Way used

Way 1 (`cd probes && BACKEND=claude PRICE_THREADS=4 python3 run_sonnet_price.py claude-sonnet-5 sonnetcloud f2_test30`),
unchanged script. Output: data/jev_f2_test30_sonnetcloud_r0.jsonl. Way 2 not needed.

- Priced 30, errors 0 (no rerun needed)
- Wall-clock: 57 s at 4 threads
- Costs seen: the script records cost 0 for `BACKEND=claude` (no per-call price is kept), so the only cost figure seen
  is the step-1 call's total_cost_usd = $0.0104 (API-equivalent). Which balance was charged (cloud credit or plan
  usage) cannot be seen from inside the session; check on claude.ai.

## Comparison with data/jev_holes_android_fw_sonnetp_r0.jsonl (match on cls+sig)

| Measure | Value |
| --- | --- |
| Methods matched | 30 / 30 (no atom-count mismatches) |
| Atoms matched | 107 |
| Mean absolute difference | 0.067 |
| Share of atoms both <= 0.05 | 0.617 |
| Share differing by more than 0.3 | 0.075 (8 atoms) |
