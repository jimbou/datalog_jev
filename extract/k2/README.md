# K2: StubDroid summaries from the real Android 13 implementation

1. `mvn dependency:copy-dependencies -DoutputDirectory=lib` with `pom.xml` (soot-infoflow-summaries 2.15.1, Soot 4.7.1) into `tools/stubdroid/lib`.
2. The implementation is `tools/witness/android-all-13-robolectric-9030017.jar` (Maven Central, org.robolectric:android-all).
3. `k2_one.sh CLASS` generates one class (1 s to 25 min, up to 7 GB, 2 cores). A class summary includes its inherited methods, so only the classes of the facts are needed. `k2_all.sh` runs `data/k2_classes2_all.txt` (the 145 receipt classes ordered by the number of accepted verdicts that depend on them; the top 25 cover 88%, the top 50 cover 96%), three at a time, skipping finished classes.
4. `probes/k2_labels.py` turns the XML in `data/stubdroid_gen/` into yes / no / gap / unknown per audit fact.
