import java.io.*;
import java.lang.reflect.*;
import java.util.*;

/** Reads "class<TAB>method signature" lines from stdin and prints "class<TAB>signature<TAB>kind" where kind is
 *  interface (an interface method without a body), abstract, native, concrete or constructor. Run against android.jar:
 *  java -cp tools/android/android.jar probes/MethodKinds.java < facts.tsv */
public class MethodKinds {
    static Class<?> type(String n, ClassLoader cl) throws Exception {
        int dims = 0;
        while (n.endsWith("[]")) { dims++; n = n.substring(0, n.length() - 2); }
        Class<?> c;
        switch (n) {
            case "int": c = int.class; break; case "long": c = long.class; break; case "short": c = short.class; break;
            case "byte": c = byte.class; break; case "boolean": c = boolean.class; break; case "char": c = char.class; break;
            case "float": c = float.class; break; case "double": c = double.class; break; case "void": c = void.class; break;
            default: c = Class.forName(n, false, cl);
        }
        for (int i = 0; i < dims; i++) c = Array.newInstance(c, 0).getClass();
        return c;
    }

    public static void main(String[] a) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        ClassLoader cl = MethodKinds.class.getClassLoader();
        for (String line; (line = in.readLine()) != null; ) {
            String[] p = line.split("\t");
            String kind = "unknown";
            try {
                Class<?> c = Class.forName(p[0], false, cl);
                String sig = p[1];
                int sp = sig.indexOf(' '), lp = sig.indexOf('('), rp = sig.lastIndexOf(')');
                String name = sig.substring(sp + 1, lp), ps = sig.substring(lp + 1, rp);
                if (name.equals("<init>")) {
                    kind = "constructor";
                } else {
                    List<Class<?>> pt = new ArrayList<>();
                    if (!ps.isEmpty()) for (String s : ps.split(",")) pt.add(type(s, cl));
                    Method m = null;
                    for (Class<?> k = c; k != null && m == null; k = k.getSuperclass()) {
                        try { m = k.getDeclaredMethod(name, pt.toArray(new Class<?>[0])); } catch (NoSuchMethodException e) { }
                    }
                    if (m == null) for (Class<?> i : c.getInterfaces()) {
                        try { m = i.getMethod(name, pt.toArray(new Class<?>[0])); break; } catch (NoSuchMethodException e) { }
                    }
                    if (m == null) {
                        kind = "not found";
                    } else {
                        int mod = m.getModifiers();
                        kind = Modifier.isNative(mod) ? "native"
                             : Modifier.isAbstract(mod) ? (m.getDeclaringClass().isInterface() ? "interface" : "abstract") : "concrete";
                    }
                }
            } catch (Throwable t) { kind = "error " + t.getClass().getSimpleName(); }
            System.out.println(p[0] + "\t" + p[1] + "\t" + kind);
        }
    }
}
