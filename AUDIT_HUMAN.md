# Human source check: 27 facts, about one hour

**File to fill in:** `/home/jim/datalog_jev/data/audit/human_source_check.csv` (27 rows, open it in a spreadsheet).
You fill five columns: `answer`, `reason_code`, `mechanism`, `evidence`, `checked_by`.

## Why this matters

Our tool says an app's code is "safe" because certain library methods do not pass secret data on. Those 27 facts are the ones
that earlier AI passes marked `yes` (the secret does get through, 9 facts) or could not decide (18 facts). A person reading
the real Android source on these 27 is what turns "an AI-assisted audit" into a defensible one. Your answers can differ from
the AI's, and that is the point. **Do not open** any other file in `data/audit/` or anything in `data/audit_private/` before
you finish, so your answers stay independent.

## What you need

- A browser and this file. No code to run.
- Android version: **Android 13**, tag `android-13.0.0_r1`. Every `source_file` link in the CSV already points at that tag.
  `java.*` classes are read from Android's own copy (`libcore/ojluni`), also linked.
- About 2 to 3 minutes per concrete method and 1 minute per callback or interface row, so roughly one hour in total.
  Rows are sorted by how many of our "safe" verdicts depend on the fact, most important first. If you stop early, the top
  rows are the ones that matter.

## The question on every row

Method M is called. **X** (`secret_starts_in`) holds a secret before the call.
After the call, is a piece of the secret in **Y** (`does_it_end_up_in`)?

"The receiver object (this)" is the object the method is called on. "argument 0, 1, ..." are the inputs in order.
"The return value" is what the method returns.

## The definition of a flow (use exactly this)

There is a flow from X to Y if X's **data** can end up in Y:

1. **Copy or compute:** Y gets X's value, or something computed from it (concatenated, parsed, encoded, cut, counted, converted).
2. **Store:** the method's purpose is to keep X, or a reference to X, in Y (add, put, set, append, attach, queue).
3. **Read out:** Y is something you can read out of X: its contents, a field, its size, its emptiness.

It is **not** a flow when X only **steers**: X chooses which existing thing is used or returned (an index, a key, a resource
ID, a flag, a charset), or controls how much, when or whether (a count, a delay, a switch), and none of X's data goes into Y.
Also not a flow: caches, counters and back-pointers that hold nothing from X, and anything that happens only through a custom
override, a callback you supply, another OS version or an unusual argument. Judge the **ordinary, documented** behavior.

Test: *is a piece of X, its value or a reference to it, now sitting in Y?* If yes, flow. If X only picked or steered, no.

## Step by step, for each row

1. Open the link in `source_file` (Android 13). Use the browser's find (Ctrl+F) to jump to the method name; match the
   parameter types in `method`, because there are overloads. Inner classes (`Outer$Inner`) are in the outer class's file.
2. Read the method body. If it calls another method that moves the data (for example `mFoo.put(key, value)` or `new File(dir,
   prefix + ...)`), click through to that method and read it too, one level is usually enough. Inherited methods are in the
   parent class (the page's `extends` line tells you which).
3. Ask the test above for exactly this X and Y.
4. Fill the row:
   - `answer`: `yes`, `no` or `unsure` (lowercase). `unsure` is a real answer. Use it when you cannot decide from the source and
     the documentation, and say why in `mechanism`. Do not guess in either direction.
   - `reason_code`: one letter from the table below. It has to match the answer.
   - `mechanism`: one sentence. For a `yes`: "X goes into Y by (what the code does)". For a `no`: why not ("the index only picks
     which element is returned").
   - `evidence`: where you saw it: the line number or the name of the called method (for example `Bundle.java L1234: mMap.put`).
   - `checked_by`: your name. If an AI helped you with a row, write that too ("name + AI"). We state this honestly in the paper.

## Rows where there is no body to read

- **Interface or abstract method** (the hint in the CSV says so): there is no implementation to read in that file. Use the
  Javadoc contract and the usual implementation named in the hint. If the documented contract says data passes (for example a
  parent receives the values), answer `yes` (code `C`, `S` or `R`). If the contract is silent and implementations may differ,
  answer `unsure`. If the only way data could pass is a custom override or callback you would supply, that is code `H` and the
  answer is `no`.
- **Native method** (reflection, `native` keyword): answer `unsure` unless the Javadoc settles it.

## Reason codes

| Code | Meaning | Answer |
| --- | --- | --- |
| `C` | **Copy or compute**: Y gets X's value or something computed from it | `yes` |
| `S` | **Store**: the method keeps X, or a reference to X, in Y | `yes` |
| `R` | **Read out**: Y is read out of X (contents, a field, size, emptiness) | `yes` |
| `P` | **Pick**: X only chooses which existing thing is used or returned | `no` |
| `K` | **Control**: X only controls how much, when or whether | `no` |
| `I` | **Incidental**: caches, counters, back-pointers, plumbing with nothing from X | `no` |
| `H` | **Hypothetical**: only through a custom override, callback, other OS version or unusual argument | `no` |
| `N` | **None**: no connection | `no` |
| `U` | **Unsure**: cannot be decided from the source and documentation | `unsure` |

## A worked example (not in your file)

`String substring(int,int)`, X = the receiver, Y = the return value. Source: `java/lang/String.java`, the method creates a new
`String` from a slice of `value`. Answer `yes`, code `C`, mechanism "the result is cut from the receiver's characters",
evidence "String.java: substring calls new String(value, beginIndex, subLen)".
The same method with X = argument 0 (the start index) and Y = the return value is `no`, code `P`: the index only picks where to cut.

## When you are done

Save the CSV in place and tell me. I will:

1. compare your answers with the AI audit and with the answer key (how often they agree, and on which facts they differ);
2. recompute the headline clearance rates with your answers in place of the AI's on these 27 facts;
3. write the result into `FINDINGS.md`, and describe the audit as human-checked for these facts.

If some rows take much longer than expected, skip them, answer `unsure` and note why. The top rows matter most.
