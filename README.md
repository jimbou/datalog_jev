# Soundiness with Receipts

Certified miss-risk for the "no leak" verdicts of an unsound taint analysis: every clean verdict
gets a receipt (the cheapest set of assumed-absent library flows it depends on, by min-cut),
each assumption is priced by Jev, and the acceptance threshold is calibrated per app on held-out
apps (Learn-then-Test). Results and their history are in `FINDINGS.md`; the paper plan is in
`ISSTA 2027 plan.md`; the original idea is in `llm_convo.md`.

## Layout

| Path | What |
| --- | --- |
| `extract/` | Soot fact extractors: apps (`Facts.java`, `extract_apks.py`), library code (`LibFacts.java`) |
| `analysis/` | Soufflé taint analysis (`taint.dl`), graph build (`run_android.py`), pricing and cuts (`evaluate.py`), calibration (`app_ltt.py`, `k1_summary.py`), closing loop (`closing*.py`, `lib.dl`) |
| `probes/` | Hole labels from FlowDroid summaries, Jev / LLM / Sonnet pricing and labeling, witness tests, static checker |
| `data/` | Kept inputs only: FlowDroid summaries and source/sink list, Jev prices, Sonnet labels, witness results |

## Setup

Not in the repo (large or downloadable); fetch into `tools/` and `bench/`:

- Soufflé 2.5: unpack the Ubuntu .deb into `tools/souffle/` (`tools/souffle.sh` wraps it)
- `tools/soot-4.6.0-jar-with-dependencies.jar` (Maven Central, `org.soot-oss:soot`)
- `tools/android/android.jar` (android-33, Sable/android-platforms)
- `tools/witness/android-all-13-robolectric-9030017.jar` (Maven Central, `org.robolectric:android-all`)
- APKs: the F-Droid files listed in `bench/apks/pick*.txt` (https://f-droid.org/repo/<apk>)
- Python: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- The JDK here has no `javac` binary; `tools/bin/javac` runs the compiler module instead.
- API keys: `OPENROUTERS_MINE` (OpenRouter) for Jev and the LLM scripts.

## Rebuild

```
.venv/bin/python analysis/run_android.py            # graphs -> data/graphs/
.venv/bin/python analysis/evaluate.py choice-obj    # verdicts with Jev prices
.venv/bin/python analysis/app_ltt.py choice-obj     # certified clearance, held-out apps
```
