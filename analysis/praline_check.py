"""Praline-style comparison on the reachability fragment: the exact "unknown correlation" optimum against max-flow.

Setting (what Praline solves when only the marginal probability of each input fact is known and the facts may
be arbitrarily correlated): given edges e with marginal probability p_e of being present, what is the largest
probability, over all joint distributions with these marginals, that a path from the source to the sink is present?
Claim: it equals min(1, max-flow with capacities p_e) = min(1, min-cut). Proof sketch: for any cut C, a path needs
at least one edge of C, so P <= sum_{e in C} p_e (union bound). Conversely decompose a maximum flow of value F <= 1
into paths with flows f_k; let world k (probability f_k) contain exactly the edges of path k, and pad with extra
edges so that every marginal is met (flow conservation gives sum of f_k through e <= p_e); the sink is reachable
with probability >= F.
This script checks the claim numerically on random small graphs by solving the exact problem as a linear program
over all 2^m worlds, and reports the cost of that naive formulation against max-flow. It is not Praline's own
algorithm (which avoids enumerating worlds); it is the optimum that algorithm approximates from above.

Usage: praline_check.py [--graphs N] [--maxm M] [--seed S]
"""
import argparse, itertools, random, time
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

SCALE = 10 ** 6


def random_graph(rng, m):
    need = next(k for k in range(4, 12) if k * (k - 1) // 2 >= m)  # enough node pairs for m edges
    n = rng.randint(need, need + 2)
    edges = set()
    while len(edges) < m:
        u, v = rng.randrange(n - 1), rng.randrange(1, n)
        if u < v:
            edges.add((u, v))
    edges = sorted(edges)
    p = [round(rng.uniform(0.05, 0.9), 3) if rng.random() < 0.8 else 1.0 for _ in edges]
    return n, edges, p


def connected(n, edges, mask):
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for k, (a, b) in enumerate(edges):
            if mask >> k & 1 and a == u and b not in seen:
                seen.add(b)
                stack.append(b)
    return (n - 1) in seen


def exact_lp(n, edges, p):
    m = len(edges)
    worlds = range(1 << m)
    c = np.array([-1.0 if connected(n, edges, w) else 0.0 for w in worlds])
    A = np.zeros((m + 1, 1 << m))
    for w in worlds:
        for k in range(m):
            if w >> k & 1:
                A[k, w] = 1.0
    A[m, :] = 1.0
    res = linprog(c, A_eq=A, b_eq=np.array(p + [1.0]), bounds=(0, None), method="highs")
    return -res.fun


def flow_bound(n, edges, p):
    rows, cols, caps = zip(*[(a, b, max(1, int(round(x * SCALE)))) for (a, b), x in zip(edges, p)])
    G = csr_matrix((np.array(caps, dtype=np.int32), (rows, cols)), shape=(n, n))
    return min(1.0, maximum_flow(G, 0, n - 1).flow_value / SCALE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graphs", type=int, default=60)
    ap.add_argument("--maxm", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    print("%-3s %-7s %-12s %-12s %-12s %-12s %-12s" % ("m", "graphs", "max |LP-flow|", "LP time (s)", "flow time (s)", "mean bound", "vs indep."))
    for m in range(5, a.maxm + 1, 1):
        diffs, tl, tf, bounds, gaps = [], 0.0, 0.0, [], []
        for _ in range(a.graphs if m <= 10 else max(10, a.graphs // 4)):
            n, edges, p = random_graph(rng, m)
            t = time.time(); lp = exact_lp(n, edges, p); tl += time.time() - t
            t = time.time(); fl = flow_bound(n, edges, p); tf += time.time() - t
            diffs.append(abs(lp - fl)); bounds.append(fl)
            # exact probability under independence, for contrast
            ind = sum(np.prod([p[k] if w >> k & 1 else 1 - p[k] for k in range(m)]) for w in range(1 << m) if connected(n, edges, w))
            gaps.append(fl - ind)
        print("%-3d %-7d %-12.2e %-12.4f %-12.5f %-12.3f %-12.3f" % (m, len(diffs), max(diffs), tl, tf, sum(bounds) / len(bounds), sum(gaps) / len(gaps)))


if __name__ == "__main__":
    main()
