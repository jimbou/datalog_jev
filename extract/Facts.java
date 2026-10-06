import java.io.*;
import java.nio.file.*;
import java.util.*;
import soot.*;
import soot.jimple.*;
import soot.options.Options;

/**
 * Soot-based fact extractor. Writes TSV relations for every concrete method of
 * application classes whose name starts with the given prefix.
 *
 * Usage: Facts <classesDir> <depsClasspath> <appPrefix> <outDir>
 *        Facts <app.apk> <android.jar> <appPrefix> <outDir>
 */
public class Facts {
    static final Map<String, PrintWriter> OUT = new HashMap<>();
    static Path outDir;
    static String prefix;
    /** Set by LibFacts: extra facts used only by the library checker (analysis/lib.dl). */
    static boolean libMode = false;

    public static void main(String[] a) throws Exception {
        String classes = a[0];
        prefix = a[2];
        outDir = Paths.get(a[3]);
        Files.createDirectories(outDir);
        G.reset();
        Options o = Options.v();
        o.set_process_dir(List.of(classes));
        o.set_allow_phantom_refs(true);
        if (classes.endsWith(".apk")) {
            o.set_src_prec(Options.src_prec_apk);
            o.set_force_android_jar(a[1]);
            o.set_process_multiple_dex(true);
        } else {
            o.set_soot_classpath(classes + File.pathSeparator + a[1]);
            o.set_src_prec(Options.src_prec_only_class);
        }
        o.set_output_format(Options.output_format_none);
        o.set_keep_line_number(true);
        o.setPhaseOption("jb", "use-original-names:true");
        Scene.v().loadNecessaryClasses();

        List<SootClass> app = new ArrayList<>();
        for (SootClass c : Scene.v().getApplicationClasses())
            if (c.getName().startsWith(prefix)) app.add(c);
        for (SootClass c : app) {
            emit("Class", c.getName(), c.isInterface() ? "interface" : "class");
            if (c.hasSuperclass()) emit("Super", c.getName(), c.getSuperclass().getName());
            for (SootClass i : c.getInterfaces()) emit("Super", c.getName(), i.getName());
            for (SootMethod m : new ArrayList<>(c.getMethods())) {
                emit("MethodDecl", c.getName(), m.getSubSignature(), m.getSignature(),
                     m.isStatic() ? "static" : "instance", m.isConcrete() ? "concrete" : "abstract");
                if (!m.isConcrete()) continue;
                try {
                    method(m, m.retrieveActiveBody());
                } catch (Exception e) {
                    System.err.println("skip " + m.getSignature() + ": " + e);
                }
            }
        }
        for (PrintWriter w : OUT.values()) w.close();
    }

    static void emit(String rel, String... cols) {
        PrintWriter w = OUT.computeIfAbsent(rel, r -> {
            try {
                return new PrintWriter(Files.newBufferedWriter(outDir.resolve(r + ".facts")));
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        });
        w.println(String.join("\t", cols));
    }

    static String v(SootMethod m, Value l) {
        return m.getSignature() + "/" + ((Local) l).getName();
    }

    static String fld(SootField f) {
        return f.getSignature();
    }

    static void method(SootMethod m, Body b) {
        String ms = m.getSignature();
        for (Local l : b.getLocals()) emit("VarType", v(m, l), l.getType().toString());
        int idx = 0;
        for (Unit u : b.getUnits()) {
            idx++;
            String site = ms + "/" + idx;
            if (u instanceof IdentityStmt) {
                IdentityStmt s = (IdentityStmt) u;
                Value r = s.getRightOp();
                if (r instanceof ThisRef) emit("ThisVar", ms, v(m, s.getLeftOp()));
                else if (r instanceof ParameterRef)
                    emit("FormalParam", ms, String.valueOf(((ParameterRef) r).getIndex()), v(m, s.getLeftOp()));
            } else if (u instanceof AssignStmt) {
                AssignStmt s = (AssignStmt) u;
                Value l = s.getLeftOp(), r = s.getRightOp();
                if (l instanceof Local) {
                    String to = v(m, l);
                    if (r instanceof InvokeExpr) call(m, site, (InvokeExpr) r, to);
                    else if (r instanceof NewExpr || r instanceof NewArrayExpr || r instanceof NewMultiArrayExpr)
                        emit("Alloc", to, site, r.getType().toString());
                    else if (r instanceof Local) emit("Move", to, v(m, r));
                    else if (r instanceof CastExpr && ((CastExpr) r).getOp() instanceof Local)
                        emit("Move", to, v(m, ((CastExpr) r).getOp()));
                    else if (r instanceof InstanceFieldRef)
                        emit("Load", to, v(m, ((InstanceFieldRef) r).getBase()), fld(((InstanceFieldRef) r).getField()));
                    else if (r instanceof StaticFieldRef)
                        emit("SLoad", to, fld(((StaticFieldRef) r).getField()));
                    else if (r instanceof ArrayRef) {
                        emit("Load", to, v(m, ((ArrayRef) r).getBase()), "[]");
                        Value ix = ((ArrayRef) r).getIndex();  // table[x]: the value depends on x
                        if (libMode && ix instanceof Local) emit("Move", to, v(m, ix));
                    }
                    else
                        for (ValueBox vb : r.getUseBoxes())
                            if (vb.getValue() instanceof Local) emit("Move", to, v(m, vb.getValue()));
                } else if (!(r instanceof Local)) {
                    if (!libMode) continue;
                    // a store of a constant or expression result (used for implicit flows in lib.dl)
                    if (l instanceof InstanceFieldRef)
                        emit("StoreC", v(m, ((InstanceFieldRef) l).getBase()), fld(((InstanceFieldRef) l).getField()));
                    else if (l instanceof ArrayRef)
                        emit("StoreC", v(m, ((ArrayRef) l).getBase()), "[]");
                } else {
                    if (l instanceof InstanceFieldRef)
                        emit("Store", v(m, ((InstanceFieldRef) l).getBase()), fld(((InstanceFieldRef) l).getField()), v(m, r));
                    else if (l instanceof StaticFieldRef)
                        emit("SStore", fld(((StaticFieldRef) l).getField()), v(m, r));
                    else if (l instanceof ArrayRef)
                        emit("Store", v(m, ((ArrayRef) l).getBase()), "[]", v(m, r));
                }
            } else if (u instanceof InvokeStmt) {
                call(m, site, ((InvokeStmt) u).getInvokeExpr(), "-");
            } else if (u instanceof ReturnStmt) {
                Value r = ((ReturnStmt) u).getOp();
                if (r instanceof Local) emit("RetVar", ms, v(m, r));
            }
        }
    }

    static void call(SootMethod m, String site, InvokeExpr e, String ret) {
        SootMethodRef ref = e.getMethodRef();
        String kind = e instanceof StaticInvokeExpr ? "static"
                : e instanceof SpecialInvokeExpr ? "special"
                : e instanceof DynamicInvokeExpr ? "dynamic" : "virtual";
        String base = e instanceof InstanceInvokeExpr ? v(m, ((InstanceInvokeExpr) e).getBase()) : "-";
        emit("Call", site, m.getSignature(), kind, ref.getDeclaringClass().getName(),
             ref.getSubSignature().toString(), base, ret);
        for (int i = 0; i < e.getArgCount(); i++) {
            Value arg = e.getArg(i);
            emit("Arg", site, String.valueOf(i),
                 arg instanceof Local ? v(m, arg)
                 : arg instanceof StringConstant ? "str:" + ((StringConstant) arg).value.replace("\t", " ").replace("\n", " ")
                 : arg instanceof ClassConstant ? "cls:" + ((ClassConstant) arg).toSootType().toString()  // e.g. new Intent(ctx, Foo.class)
                 : "-");
        }
    }
}
