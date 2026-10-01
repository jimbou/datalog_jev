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

## Unattended runs

`bench/receipts-build.service` is a systemd *user* unit (install to `~/.config/systemd/user/`, then
`systemctl --user daemon-reload && systemctl --user enable --now receipts-build.service`; needs
`loginctl enable-linger`). It restarts the build after a crash or reboot. The driver is safe to
restart at any time: graphs are written atomically and re-checked on start, apps that ran out of
memory are listed in `data/android_failed.txt`, apps that hit a bug in `data/android_errors.txt`, and
an app that has crashed the run three times (`data/android_attempts.txt`) is skipped.

Status: `systemctl --user status receipts-build.service`; progress: `tail data/build_server.log`.
Stop: `systemctl --user stop receipts-build.service` (disable it to keep it from starting at boot).
