# Running the pipeline on a remote Linux box (no root)

State prepared on the remote machine (home directory, nothing system-wide):

- `~/receipts/`: clone of this repo (git bundle), plus the untracked inputs: `tools/souffle*`,
  `tools/soot-4.6.0-jar-with-dependencies.jar`, `tools/android/android.jar`, and `data/graphs/`
  (copied with rsync).
- `~/jdk/`: Temurin JDK 21 (from a mirror, unpacked). `source ~/receipts/env.sh` puts it on PATH and
  changes into the repo. The local `tools/bin/javac` shim is not needed there.
- APKs in `~/receipts/bench/apks/`, fetched from a nearby F-Droid mirror (`FDROID_BASE`); the mirror
  was ~1000x faster than f-droid.org from the remote network.

## Build graphs (the memory-heavy step)

```
source ~/receipts/env.sh
export JOBS=1 SOUFFLE_MEM_GB=12      # raise both with more RAM; each Soufflé run needs up to the cap
python3 analysis/run_android.py      # builds data/graphs/<app>.npz for every APK in bench/apks/pick*.txt
```

With ~60 GB RAM, `JOBS=3 SOUFFLE_MEM_GB=16` is reasonable. Apps that exceed the cap are listed in
`data/android_failed.txt` and skipped on later runs (delete a line to retry it with a higher cap).

## Evaluate (cheap, CPU-bound)

```
python3 analysis/evaluate.py choice-obj          # also: uniform, freq, k1-<rate>-<seed>-<pricing>
python3 analysis/app_ltt.py choice-obj --alpha 0.05 --eps 0.05
```

`evaluate.py` needs the Jev price files in `data/` (tracked). Calls to the pricing APIs need the
OpenRouter key and, from China, the local proxy; pass keys per command, never in the command line.

## Moving results back

`rsync -a pku:receipts/data/graphs/ data/graphs/` (about 1 MB per app). Result files
(`data/android_*.jsonl`) are regenerable and not tracked.
