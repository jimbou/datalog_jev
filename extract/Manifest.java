import java.io.*;
import java.util.*;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.manifest.ProcessManifest;

/**
 * Dump the components of an APK's manifest for the inter-component holes (experiment 4).
 * Usage: java -cp <flowdroid jars> extract/Manifest.java APK OUT_DIR
 * Writes OUT_DIR/Component.facts (class TAB kind TAB exported) and OUT_DIR/IntentFilter.facts (class TAB action), where kind is
 * activity, service, receiver or provider (activity-alias counts as an activity of its target).
 */
public class Manifest {
    static String attr(AXmlNode n, String name) {
        AXmlAttribute<?> a = n.getAttribute(name);
        return a == null || a.getValue() == null ? null : a.getValue().toString();
    }

    static String full(String pkg, String name) {
        if (name == null) return null;
        if (name.startsWith(".")) return pkg + name;
        return name.contains(".") ? name : pkg + "." + name;
    }

    public static void main(String[] args) throws Exception {
        String apk = args[0];
        File out = new File(args[1]);
        out.mkdirs();
        try (ProcessManifest pm = new ProcessManifest(apk);
             PrintWriter comp = new PrintWriter(new FileWriter(new File(out, "Component.facts")));
             PrintWriter filt = new PrintWriter(new FileWriter(new File(out, "IntentFilter.facts")))) {
            String pkg = pm.getPackageName();
            for (AXmlNode app : pm.getManifest().getChildrenWithTag("application")) {
                for (AXmlNode c : app.getChildren()) {
                    String tag = c.getTag();
                    String kind = tag.equals("activity") || tag.equals("activity-alias") ? "activity"
                            : tag.equals("service") ? "service" : tag.equals("receiver") ? "receiver"
                            : tag.equals("provider") ? "provider" : null;
                    if (kind == null) continue;
                    String name = full(pkg, tag.equals("activity-alias") ? attr(c, "targetActivity") : attr(c, "name"));
                    if (name == null) continue;
                    boolean hasFilter = !c.getChildrenWithTag("intent-filter").isEmpty();
                    String exp = attr(c, "exported");
                    comp.println(name + "\t" + kind + "\t" + (exp != null ? exp : (hasFilter ? "true" : "false")));
                    for (AXmlNode f : c.getChildrenWithTag("intent-filter"))
                        for (AXmlNode a : f.getChildrenWithTag("action")) {
                            String act = attr(a, "name");
                            if (act != null) filt.println(name + "\t" + act);
                        }
                }
            }
        }
    }
}
