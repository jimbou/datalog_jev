# Audit task: does the secret get through?

**File to fill in:** `/home/jim/datalog_jev/data/audit/audit_facts.csv` (446 rows, open it in any spreadsheet or editor).
Fill the `answer` column. Do as many rows as you like, from the top. Save the file in the same place.

## Why

Our tool says some app code is "safe" because certain library methods do not pass secret data along. That claim
was labeled by FlowDroid and by an AI model. We want an independent check by you, so please do not look at any
other file in `data/` while answering.

## The question on every row

A row names a library method (`class` and `method`) and two places in it:

- `secret_starts_in`: where we imagine a secret is **before** the method runs.
- `does_it_end_up_in`: the place we ask about **after** the method has run.

> Suppose the secret is in `secret_starts_in` before the call. After the call, does `does_it_end_up_in`
> hold that secret, or anything taken or built from it?

Places are written as: `the receiver object (this)` (the object the method is called on), `argument 0`,
`argument 1`, ... (the inputs, with their types), or `the return value`.

## The rule to use (important, the same one the tool uses)

Count a place as holding the secret if it could contain the secret **or anything obtained from it**:
its fields, its contents, anything read out of it, or any value computed from it. A secret object makes
everything you can get out of it secret.

## What to write in `answer`

| Write | When |
| --- | --- |
| `yes` | the secret can end up there |
| `no` | the method cannot pass the secret there |
| `unsure` | you cannot tell (a real answer, please do not guess) |

Use exactly those lowercase words. The `notes` column is optional (one short line, for example "docs say it only logs").

## Three worked examples (not in the file)

| Method | secret starts in | ends up in | Answer | Why |
| --- | --- | --- | --- | --- |
| `String concat(String)` | argument 0 | the return value | `yes` | the result contains argument 0 |
| `String trim()` | the receiver | the return value | `yes` | the result is built from the receiver |
| `String concat(String)` | the receiver | argument 0 | `no` | the method does not change its argument |

If a method's behavior is not obvious, the Android reference has every class:
`https://developer.android.com/reference/<package path>/<Class>`, for example
`https://developer.android.com/reference/android/os/Bundle`. The Java classes are on the same site.

## Order and effort

The rows are sorted by how many of our "safe" verdicts depend on them, most important first.
Rows 1 to 50 carry about 81% of the dependence and rows 1 to 100 about 91%. If you only have time for part
of it, do the first 100. About 100 to 150 rows an hour is a normal pace.

## When you are done

Save the CSV, then tell me. I will compare your answers with the labels we used, report how often they agree
(overall and for the AI-labeled facts), and say what the disagreements do to our results.
