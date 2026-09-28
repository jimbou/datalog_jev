import java.io.*;
import java.nio.file.*;
import java.util.*;
import soot.*;
import soot.jimple.*;
import soot.options.Options;

/**
 * Fact extractor for library code (oracle 1 of the closing loop). Starting from the given
 * library methods, emits the same relations as Facts for their bodies and for every method they
 * call, up to a call depth. Extra relations:
 *   Root(sig)                 a method whose flows are asked about (from the targets file)
 *   Resolved(site, callee)    a call resolved to a body that was also extracted
 *   Frontier(site)            a call with no usable body: native, abstract or interface target
 *                             without a single implementation, phantom, or beyond the depth bound
 *   RootNoBody(sig)           a root with no body (interface or native method)
 * Virtual calls resolve to the implementation visible from the declared type (a documented
 * approximation: overrides in subclasses are not followed).
 *
 * Usage: LibFacts <sootClasspath> <targets.tsv: class TAB subsignature> <depth> <outDir>
 */
public class LibFacts {
    public static void main(String[] a) throws Exception {
        int depth = Integer.parseInt(a[2]);
        Facts.outDir = Paths.get(a[3]);
        Files.createDirectories(Facts.outDir);
        Facts.prefix = "";
        Facts.libMode = true;
        G.reset();
        Options o = Options.v();
        o.set_soot_classpath(a[0]);
        o.set_allow_phantom_refs(true);
        o.set_src_prec(Options.src_prec_only_class);
        o.set_output_format(Options.output_format_none);
        o.setPhaseOption("jb", "use-original-names:true");
        Scene.v().loadBasicClasses();

        Deque<Object[]> work = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        for (String line : Files.readAllLines(Paths.get(a[1]))) {
            String[] p = line.split("\t");
            if (p.length < 2) continue;
            SootMethod m = find(p[0], p[1]);
            String sig = "<" + p[0] + ": " + p[1] + ">";
            if (m == null || !m.isConcrete()) {
                Facts.emit("RootNoBody", sig);
                continue;
            }
            Facts.emit("Root", m.getSignature());
            if (!m.getSignature().equals(sig)) Facts.emit("RootAlias", sig, m.getSignature());
            work.add(new Object[]{m, 0});
        }
        while (!work.isEmpty()) {
            Object[] w = work.poll();
            SootMethod m = (SootMethod) w[0];
            int d = (Integer) w[1];
            if (!seen.add(m.getSignature())) continue;
            Body b;
            try {
                b = m.retrieveActiveBody();
            } catch (Exception e) {
                continue;
            }
            Facts.method(m, b);
            for (Local l : b.getLocals()) Facts.emit("Local", m.getSignature(), Facts.v(m, l));
            int idx = 0;
            for (Unit u : b.getUnits()) {
                idx++;
                // locals a branch depends on (control dependence is handled coarsely in lib.dl)
                Value cond = u instanceof IfStmt ? ((IfStmt) u).getCondition()
                        : u instanceof SwitchStmt ? ((SwitchStmt) u).getKey() : null;
                if (cond != null)
                    for (ValueBox vb : cond.getUseBoxes())
                        if (vb.getValue() instanceof Local) Facts.emit("IfUse", m.getSignature(), Facts.v(m, vb.getValue()));
                if (cond instanceof Local) Facts.emit("IfUse", m.getSignature(), Facts.v(m, cond));
                InvokeExpr e = u instanceof Stmt && ((Stmt) u).containsInvokeExpr() ? ((Stmt) u).getInvokeExpr() : null;
                if (e == null) continue;
                String site = m.getSignature() + "/" + idx;
                SootMethod callee = resolve(e);
                if (callee == null || !callee.isConcrete() || d + 1 > depth) {
                    Facts.emit("Frontier", site);
                } else {
                    Facts.emit("Resolved", site, callee.getSignature());
                    work.add(new Object[]{callee, d + 1});
                }
            }
        }
        for (PrintWriter w : Facts.OUT.values()) w.close();
    }

    /** An instance method whose code may be replaced by a subclass we cannot see. */
    static boolean overridable(SootClass c, SootMethod m) {
        return !m.isStatic() && !m.isPrivate() && !m.isFinal() && !m.isConstructor()
                && (c.isAbstract() || c.isInterface() || m.getDeclaringClass().isAbstract());
    }

    static SootMethod find(String cls, String sub) {
        try {
            SootClass c = Scene.v().loadClassAndSupport(cls);
            c.setApplicationClass();
            for (SootClass k = c; k != null; k = k.hasSuperclass() ? k.getSuperclass() : null) {
                SootMethod m = k.getMethodUnsafe(sub);
                if (m != null) return overridable(c, m) ? null : m;
            }
        } catch (Exception e) {
        }
        return null;
    }

    static SootMethod resolve(InvokeExpr e) {
        try {
            if (e instanceof DynamicInvokeExpr) return null;
            SootMethodRef ref = e.getMethodRef();
            SootClass c = Scene.v().loadClassAndSupport(ref.getDeclaringClass().getName());
            if (c.isPhantom()) return null;
            if (e instanceof StaticInvokeExpr || e instanceof SpecialInvokeExpr) return ref.resolve();
            if (c.isInterface()) return null;
            for (SootClass k = c; k != null; k = k.hasSuperclass() ? k.getSuperclass() : null) {
                SootMethod m = k.getMethodUnsafe(ref.getSubSignature());
                if (m != null) return m.isAbstract() || overridable(c, m) ? null : m;
            }
        } catch (Exception ex) {
        }
        return null;
    }
}
