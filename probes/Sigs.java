import java.io.*;
import java.lang.reflect.*;
import java.util.*;

// Reads "class<TAB>ret name(p1,p2)" lines on stdin, prints "found<TAB>static<TAB>line"
// for each, resolving the method on the running JDK (walking supertypes).
public class Sigs {
    public static void main(String[] a) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        String line;
        while ((line = in.readLine()) != null) {
            String[] parts = line.split("\t");
            String found = "missing", stat = "?";
            try {
                Class<?> c = Class.forName(parts[0]);
                String sig = parts[1];
                String ret = sig.substring(0, sig.indexOf(' '));
                String rest = sig.substring(sig.indexOf(' ') + 1);
                String name = rest.substring(0, rest.indexOf('('));
                String ps = rest.substring(rest.indexOf('(') + 1, rest.length() - 1);
                String[] want = ps.isEmpty() ? new String[0] : ps.split(",");
                for (Method m : allMethods(c)) {
                    if (!m.getName().equals(name) || m.getParameterCount() != want.length) continue;
                    if (!m.getReturnType().getTypeName().equals(ret)) continue;
                    boolean ok = true;
                    Class<?>[] pt = m.getParameterTypes();
                    for (int i = 0; i < pt.length; i++)
                        if (!pt[i].getTypeName().equals(want[i])) ok = false;
                    if (ok) {
                        found = "found";
                        stat = Modifier.isStatic(m.getModifiers()) ? "static" : "instance";
                        break;
                    }
                }
                if (found.equals("missing") && name.equals("<init>")) {
                    found = "found";
                    stat = "ctor";
                }
            } catch (Throwable t) {
                found = "noclass";
            }
            System.out.println(found + "\t" + stat + "\t" + line);
        }
    }

    static List<Method> allMethods(Class<?> c) {
        List<Method> out = new ArrayList<>();
        Deque<Class<?>> q = new ArrayDeque<>(List.of(c));
        Set<Class<?>> seen = new HashSet<>();
        while (!q.isEmpty()) {
            Class<?> k = q.poll();
            if (k == null || !seen.add(k)) continue;
            out.addAll(Arrays.asList(k.getDeclaredMethods()));
            if (k.getSuperclass() != null) q.add(k.getSuperclass());
            q.addAll(Arrays.asList(k.getInterfaces()));
        }
        return out;
    }
}
