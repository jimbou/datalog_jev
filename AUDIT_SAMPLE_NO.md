# Second human check: 40 "no flow" facts, about an hour

**File to fill in:** `/home/jim/datalog_jev/data/audit/human_sample2.csv` (40 rows, open it in a spreadsheet).
You fill five columns: `answer`, `reason_code`, `mechanism`, `evidence`, `checked_by`.

## Why this matters

In the first check you read the 27 facts the AI passes had flagged as `yes` or `unsure`. That tells us how the AI's flags
hold up, but not how often the AI's **`no`** answers are wrong, and the "safe" verdicts depend on the `no` answers. Here are 40
facts the AI passes called `no` (no flow). A person looks for the line of code where the secret does get through. If a
person finds a flow in a few of them, we learn the AI's miss rate; if in none, we can say so with a number.

The 40 are drawn in two ways (you are not told which row is which): 12 of the facts that most verdicts depend on, chosen for
sure, and 28 chosen at random from the rest. The rows are in random order. **Do not open** any other file in
`data/audit/` or anything in `data/audit_private/` until you finish, so your answers stay independent.

## What you need

- A browser and this file. No code to run.
- Android version **Android 13**, tag `android-13.0.0_r1`. Every `source_file` link already points at that tag (`java.*`
  classes: Android's own copy, `libcore/ojluni`).
- About 1.5 to 2 minutes per row, so about an hour. The `hint` column says whether the method has a body to read (concrete,
  constructor) or not (interface, abstract).

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
ID, a flag), or controls how much, when or whether (a count, a delay, a switch), and none of X's data goes into Y. Also not a
flow: caches, counters and back-pointers that hold nothing from X, and anything that happens only through a custom override,
a callback you supply, another OS version or an unusual argument. Judge the **ordinary, documented** behavior.

Test: *is a piece of X, its value or a reference to it, now sitting in Y?*

## How to look

For these rows the AI said `no`. **Do not assume it is right.** Try to find the place where X goes into Y:

1. Open `source_file` and jump to the method (Ctrl+F, match the parameter types: there are overloads).
2. Read the body. Follow every call that takes X (or something derived from it) one level down. Look for assignments to a field of
   the receiver, to a field of an argument, and for what goes into the return value.
3. If you can name a line where X's data goes into Y, answer `yes`. If you have read the body and X only steers, or nothing of X
   reaches Y, answer `no` and say what you saw. If you cannot tell, answer `unsure`.

## What to write in each row

- `answer`: `yes`, `no` or `unsure` (lowercase). `unsure` is a real answer: use it when the source and documentation do not settle it.
  Do not guess in either direction.
- `reason_code`: one letter from the table. It has to match the answer.
- `mechanism`: one sentence. For a `yes`: "X goes into Y by (what the code does)". For a `no`: why not.
- `evidence`: where you saw it (line number, or the name of the called method).
- `checked_by`: your name. If an AI helped you with a row, write that too ("name + AI").

## Rows where there is no body to read

- **Interface or abstract method:** use the Javadoc contract and the usual implementation named in the hint. If the contract says
  data passes, answer `yes`. If it is silent and implementations may differ, answer `unsure`. If the only way data could pass is a
  custom override or callback you would supply, that is code `H` and the answer is `no`.
- **Native method:** answer `unsure` unless the Javadoc settles it.
- **Constructor:** what the arguments are stored into counts as the receiver (`this`).

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

## When you are done

Save the CSV in place and tell me. I will:

1. count how many of the AI's `no` answers a person turned into `yes` or `unsure`, and weight the two groups correctly (the
   12 sure rows count for themselves, the 28 random rows stand for the other 407 facts) to estimate the miss rate;
2. if flows are found, recompute the headline clearance rates with those facts corrected;
3. write the result into `FINDINGS.md`.

If a row takes much longer than expected, skip it, answer `unsure`, and note why.
