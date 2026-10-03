# K2: StubDroid summaries from the real Android 13 implementation

1. `mvn dependency:copy-dependencies -DoutputDirectory=lib` with `pom.xml` (soot-infoflow-summaries 2.15.1, Soot 4.7.1) into `tools/stubdroid/lib`.
2. The implementation is `tools/witness/android-all-13-robolectric-9030017.jar` (Maven Central, org.robolectric:android-all).
3. `k2_one.sh CLASS` generates one class (about 3 to 10 min, up to 7 GB); `k2_all.sh` runs the class list in `data/k2_classes.txt`, four at a time.
4. `probes/k2_labels.py` turns the XML in `data/stubdroid_gen/` into yes / no / gap / unknown per audit fact.
