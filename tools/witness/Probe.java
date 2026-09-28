import java.lang.reflect.*;
import java.util.*;

/**
 * Helper for witness tests: a test puts SRC (normally MARKER) into a method's source endpoint, calls the
 * method, then asks whether the target endpoint holds the marker. contains() searches the
 * object graph (strings, char/byte arrays, collections, maps, fields, toString) up to a bound.
 * A witness test prints exactly one of WITNESS / NO_WITNESS.
 */
public final class Probe {
    public static final String MARKER = "TAINTMARK7f3a";
    /** What a test puts into the source endpoint; the control run sets -Dsrc.marker to something else. */
    public static final String SRC = System.getProperty("src.marker", MARKER);

    public static boolean contains(Object root) {
        Deque<Object[]> q = new ArrayDeque<>();
        Set<Object> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        q.add(new Object[]{root, 0});
        int visited = 0;
        while (!q.isEmpty() && visited++ < 20000) {
            Object[] e = q.poll();
            Object o = e[0];
            int d = (Integer) e[1];
            if (o == null || !seen.add(o)) continue;
            if (hit(o)) return true;
            if (d >= 6) continue;
            Class<?> c = o.getClass();
            if (c.isArray()) {
                if (!c.getComponentType().isPrimitive())
                    for (int i = 0; i < Math.min(Array.getLength(o), 1000); i++) q.add(new Object[]{Array.get(o, i), d + 1});
                continue;
            }
            if (o instanceof Iterable<?> it) {
                try { int n = 0; for (Object x : it) { if (n++ > 1000) break; q.add(new Object[]{x, d + 1}); } } catch (Throwable t) { }
            }
            if (o instanceof Map<?, ?> m) {
                try { for (Map.Entry<?, ?> x : m.entrySet()) { q.add(new Object[]{x.getKey(), d + 1}); q.add(new Object[]{x.getValue(), d + 1}); } } catch (Throwable t) { }
            }
            for (Class<?> k = c; k != null && k != Object.class; k = k.getSuperclass()) {
                for (Field f : k.getDeclaredFields()) {
                    if (Modifier.isStatic(f.getModifiers())) continue;
                    try { f.setAccessible(true); q.add(new Object[]{f.get(o), d + 1}); } catch (Throwable t) { }
                }
            }
        }
        return false;
    }

    private static boolean hit(Object o) {
        try {
            if (o instanceof CharSequence s) return s.toString().contains(MARKER);
            if (o instanceof char[] a) return new String(a).contains(MARKER);
            if (o instanceof byte[] a) return new String(a, java.nio.charset.StandardCharsets.ISO_8859_1).contains(MARKER);
            if (o.getClass().isPrimitive() || o instanceof Number || o instanceof Boolean) return false;
            String s = String.valueOf(o);
            return s != null && s.contains(MARKER);
        } catch (Throwable t) {
            return false;
        }
    }

    public static void report(Object target) {
        System.out.println(contains(target) ? "WITNESS" : "NO_WITNESS");
    }
}
