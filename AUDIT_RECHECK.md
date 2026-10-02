# Recheck the "yes" answers: strict instructions

**File:** `/home/jim/datalog_jev/data/audit/audit_recheck.csv` (95 rows, the ones answered `yes` in the first pass).
Fill three columns on every row: `new_answer`, `reason_code`, `mechanism`. The first-pass file is untouched.

The first pass answered `yes` too easily. The main fault was counting things that **could** happen in unusual
cases. This pass answers only for the **ordinary, documented behavior**.

## The question

Method M is called with **X** holding a secret. After the call, is a piece of the secret now in **Y**?

## Judge the ordinary case only

1. Assume **plain, standard arguments**: ordinary objects of the library's own classes. Ignore what a **custom
   subclass, override, listener or callback** passed in could do. (The tool handles callbacks separately.)
2. Use the method's **documented purpose and its normal code path**. Ignore **older or newer OS versions**, special
   builds and anything you can only know from reading internals.
3. Ignore **side effects that keep nothing from X**: caches, counters, timestamps, hash or identity values, the
   method updating its own bookkeeping, parent or owner pointers, listener registration done as plumbing.
4. Do **not** answer `yes` because the secret *influences* what happens (which element, when, how many, whether).
   Influence is not a flow. Only the **data itself** (or a reference to it) in Y is a flow.

## Answer `yes` only if you can name the mechanism

Write the mechanism in one short sentence in `mechanism`, in the form
**"X goes into Y by (what the method does)"**. If you cannot write that sentence from the method's ordinary
behavior, the answer is not `yes`.

## `reason_code` (required on every row)

Use exactly one letter. The letters decide the answer, so they must match `new_answer`.

| Code | Meaning | `new_answer` |
| --- | --- | --- |
| `C` | **Copy or compute**: Y gets X's value, or something computed from it (concatenated, parsed, encoded, cut, converted) | `yes` |
| `S` | **Store**: the method's purpose is to keep X, or a reference to X, in Y (add, put, set, append, attach, enqueue) | `yes` |
| `R` | **Read out**: Y is read out of X: its contents, a field, its size, its emptiness | `yes` |
| `P` | **Pick**: X only chooses which existing thing is used or returned (index, key, resource ID, locale, charset, flag) | `no` |
| `K` | **Control**: X only controls how much, when or whether (count, delay, length limit, switch) | `no` |
| `I` | **Incidental**: caches, counters, back-pointers, registration, identity, version- or implementation-specific detail; nothing from X is meant to be kept in Y | `no` |
| `H` | **Hypothetical**: only possible through a custom subclass, callback, override, older or newer OS version, or an unusual argument | `no` |
| `N` | **None**: no connection | `no` |
| `U` | **Unsure**: you cannot tell from the documented behavior | `unsure` |

`unsure` is the honest answer when you cannot decide. It is better than a guess in either direction.
Do not choose `no` just to be safe, and do not choose `yes` just because something might happen.

## Examples (not in your file)

| Method | X | Y | Answer | Code | Mechanism / reason |
| --- | --- | --- | --- | --- | --- |
| `String substring(int,int)` | receiver | return value | `yes` | `C` | the result is cut from the receiver |
| `String substring(int,int)` | argument 0 (start index) | return value | `no` | `P` | the index only picks where to cut |
| `Map get(Object key)` | argument 0 (the key) | return value | `no` | `P` | the key only picks which value comes back |
| `Map get(Object key)` | receiver | return value | `yes` | `R` | the value is read out of the map |
| `Map put(Object key, Object value)` | argument 0 (the key) | receiver | `yes` | `S` | the key is stored in the map |
| `View void setTag(Object)` | argument 0 | receiver | `yes` | `S` | the view keeps the object as its tag |
| `StringBuilder void setLength(int)` | argument 0 | receiver | `no` | `K` | the number only controls truncation |
| `Handler boolean post(Runnable)` | receiver (the handler) | argument 0 (the runnable) | `no` | `I` | the handler sets itself as an internal target, not something to be kept as data |
| `Resources InputStream openRawResource(int)` | argument 0 (resource ID) | return value | `no` | `P` | the ID only picks which file is opened |
| `Context String getString(int)` | argument 0 (resource ID) | receiver | `no` | `I` | the context may update internal resource caches, nothing from the ID is meant to be kept |

## What I will do with it

The codes let me compute the result two ways without asking again: **strict** (answers `C`, `S`, `R` count as flows)
and **liberal** (also counting `I` and `H`). I will report both, and the rows where you chose `U`.
Please do not look at other files in `data/`. When you are done, tell me.
