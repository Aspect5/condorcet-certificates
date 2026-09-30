#!/usr/bin/env python3
"""Checker-side CNF generator and exact Farkas re-check for the m=7,k=3 certificate.

Written by the release checker; does not import independent.py.
Events are (W, c) with W a sorted k-tuple and c outside W, in the same
lexicographic order as independent.py (combinations x range(m)); the order is
re-derived here and cross-checked against independent.py's DIMACS dump.
Farkas check uses all m! full rankings (not prefixes) in exact rationals.
"""
import itertools, json, sys
from fractions import Fraction

cert_path, m, k, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
data = json.load(open(cert_path))
assert data['m'] == m and data['k'] == k and data['status'] == 'unsat' and data['orbit']

sets = list(itertools.combinations(range(m), k))
events = [(w, c) for w in sets for c in range(m) if c not in w]
eid = {e: i for i, e in enumerate(events)}
assert len(events) == data['event_count']

# Exact Farkas check over all full rankings.
rankings = list(itertools.permutations(range(m)))
def tops(r, w, c):
    pos = {x: i for i, x in enumerate(r)}
    return all(pos[c] < pos[a] for a in w)
cores = []
worst = Fraction(0)
for leaf in data['dual_leaves']:
    y = {}
    for i, s in leaf['weights']:
        q = Fraction(s)
        assert q > 0
        y[int(i)] = y.get(int(i), 0) + q
    assert sum(y.values()) == 1
    b = max(sum(q for i, q in y.items() if tops(r, *events[i])) for r in rankings)
    assert b < Fraction(1, 2), b
    worst = max(worst, b)
    cores.append(sorted(y))
    print('core', [events[i] for i in sorted(y)], 'max', b)
print('farkas: all', len(cores), 'cores verified over', len(rankings), 'full rankings; worst bound', worst)

clauses = []
for w in sets:
    ch = [eid[(w, c)] + 1 for c in range(m) if c not in w]
    clauses.append(ch)
    for u, v in itertools.combinations(ch, 2):
        clauses.append([-u, -v])
clauses.append([eid[(sets[0], k)] + 1])  # WLOG W0={0..k-1} overthrown by k
seen = set()
for p in itertools.permutations(range(m)):
    for core in cores:
        img = tuple(sorted(eid[(tuple(sorted(p[x] for x in events[i][0])), p[events[i][1]])] + 1 for i in core))
        if img not in seen:
            seen.add(img)
            clauses.append([-v for v in img])
print('distinct orbit clauses', len(seen))
with open(out, 'w') as f:
    f.write(f'p cnf {len(events)} {len(clauses)}\n')
    for cl in clauses:
        f.write(' '.join(map(str, cl)) + ' 0\n')
print('wrote', out, 'vars', len(events), 'clauses', len(clauses))
