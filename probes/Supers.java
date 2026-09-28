import java.io.*;
import java.util.*;

// Reads class names on stdin; prints "class<TAB>t1,t2,..." with the class and all
// supertypes in BFS order (Object last), or "class<TAB>" when the class is unknown.
public class Supers {
    public static void main(String[] a) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        String line;
        while ((line = in.readLine()) != null) {
            List<String> out = new ArrayList<>();
            try {
                Deque<Class<?>> q = new ArrayDeque<>(List.of(Class.forName(line, false, Supers.class.getClassLoader())));
                Set<Class<?>> seen = new HashSet<>();
                while (!q.isEmpty()) {
                    Class<?> k = q.poll();
                    if (!seen.add(k)) continue;
                    if (k != Object.class) out.add(k.getName());
                    if (k.getSuperclass() != null) q.add(k.getSuperclass());
                    q.addAll(Arrays.asList(k.getInterfaces()));
                }
                out.add("java.lang.Object");
            } catch (Throwable t) {
            }
            System.out.println(line + "\t" + String.join(",", out));
        }
    }
}
