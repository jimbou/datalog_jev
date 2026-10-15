import java.nio.file.*;
import java.util.*;
import soot.jimple.infoflow.InfoflowConfiguration;
import soot.jimple.infoflow.android.InfoflowAndroidConfiguration;
import soot.jimple.infoflow.android.SetupApplication;
import soot.jimple.infoflow.android.config.SootConfigForAndroid;
import soot.jimple.infoflow.cmd.MainClass;

/**
 * FlowDroid's command line with bundled libraries excluded, the FlowDroid counterpart of our step-e fallback (F1 e):
 * classes under the prefixes in the file named by $EXCLUDE_PREFIXES get no bodies (Soot's exclude list, as FlowDroid
 * already does for java.* and android.*), so calls into them go to the taint wrapper or are dropped; classes under
 * $KEEP_PREFIX (the app's own package) are always included.
 * Usage: same arguments as soot.jimple.infoflow.cmd.MainClass.
 */
public class FDExclude extends MainClass {
    static final List<String> EXCLUDE = new ArrayList<>(), INCLUDE = new ArrayList<>();

    public static void main(String[] args) throws Exception {
        for (String l : Files.readAllLines(Paths.get(System.getenv("EXCLUDE_PREFIXES"))))
            if (!l.isBlank() && !l.startsWith("#")) EXCLUDE.add(l.trim() + "*");
        String keep = System.getenv("KEEP_PREFIX");
        if (keep != null && !keep.isEmpty()) INCLUDE.add(keep + "*");
        new FDExclude().run(args);
    }

    @Override
    protected SetupApplication createFlowDroidInstance(InfoflowAndroidConfiguration config) {
        SetupApplication app = super.createFlowDroidInstance(config);
        app.setSootConfig(new SootConfigForAndroid() {
            @Override
            public void setSootOptions(soot.options.Options o, InfoflowConfiguration c) {
                super.setSootOptions(o, c);
                List<String> ex = new ArrayList<>(o.exclude());
                ex.addAll(EXCLUDE);
                o.set_exclude(ex);
                List<String> in = new ArrayList<>(o.include());
                in.addAll(INCLUDE);
                o.set_include(in);
                o.set_no_bodies_for_excluded(true);
                System.err.println("FDExclude: " + EXCLUDE.size() + " excluded prefixes, include " + INCLUDE);
            }
        });
        return app;
    }
}
