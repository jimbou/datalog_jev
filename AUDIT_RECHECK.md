# Recheck the "yes" answers

**File:** `/home/jim/datalog_jev/data/audit/audit_recheck.csv` (95 rows, the ones answered `yes` in the first pass).
Fill `new_answer` with `yes`, `no` or `unsure`. The first-pass file is untouched.

## Definition of a flow

There is a flow from **X** to **Y** if, when the method runs, X's **data can end up in Y**. That means one of:

1. **Copied or transformed into Y.** Anything computed from X's contents (concatenated, parsed, encoded, cut, counted,
   converted) and put into Y.
2. **Stored in Y.** Y keeps X itself, or a reference to X, so that something read from Y later can reach X
   (for example X is added to a list, set as a field, queued, or attached as a tag).
3. **Read out of X into Y.** Y is something you can get out of X: its contents, its fields, its size, whether it is empty,
   its metadata. The tool treats a whole object as secret, so anything read out of a secret object is secret.

It is **not** a flow when X only decides **what happens** and none of X's data goes into Y:

- X chooses **which** existing thing is returned or used: an index, a key, a resource ID, a locale or charset, a flag.
- X controls **how much, when or whether**: a count, a delay, a length limit, a boolean switch.
- Y changes only through **bookkeeping that holds nothing from X**: caches or counters that are updated, but not with
  X's value or a reference to X.
- A **status result** (success, true or false) that does not depend on X's contents.

Ask: *is a piece of X, its value or a reference to it, now sitting in Y?* If yes, it is a flow. If X only picked or
steered, it is not.

## Examples (not in your file)

| Method | secret starts in | ends up in | Answer | Why |
| --- | --- | --- | --- | --- |
| `String substring(int,int)` | the receiver | the return value | `yes` | the result is cut from the receiver |
| `String substring(int,int)` | argument 0 (start index) | the return value | `no` | the index only picks where to cut |
| `Map get(Object key)` | argument 0 (the key) | the return value | `no` | the key only picks which value comes back |
| `Map get(Object key)` | the receiver | the return value | `yes` | the value is read out of the map |
| `Map put(Object key, Object value)` | argument 0 (the key) | the receiver | `yes` | the key is stored in the map |
| `View void setTag(Object)` | argument 0 | the receiver | `yes` | the receiver keeps a reference to it |
| `StringBuilder void setLength(int)` | argument 0 | the receiver | `no` | the number only controls truncation |
| `String length()` | the receiver | the return value | `yes` | the length is read out of the receiver |

## Cases to mark `unsure`

Mark `unsure` (with a one-line note) when the answer depends on private implementation details you cannot confirm,
or on a result that might or might not come from the contents, such as a success flag. I would rather have an honest
`unsure` than a guess.

## Note on how this changes things

Under this definition many of your first-pass `yes` answers may well stay `yes`. If so, that means the original labels
(FlowDroid and the AI model) were too narrow, and the result moves. That is a real finding, not a mistake in your answers.
Please judge each row by the definition above, not by what you expect the result to be.

When you are done, tell me. I will compare the new answers with the key and with the first pass.
