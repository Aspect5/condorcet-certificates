#!/usr/bin/env python3
"""Independent CNF generator and exact Farkas check for m=8, k=3 (altera-lane).

Does not import search.py. Events (W, c): W a sorted 3-subset of {0..7}, c not
in W, ordered as combinations(range(8), 3) x ascending c; variable = index + 1.
A core is a list [[event_index, "p/q"], ...] with positive weights summing to 1;
it is valid iff max over all 8! full rankings of the weighted count of events the
ranking makes true is < 1/2 (exact integers, no prefixes, no floats).

Clause groups (each optional part is a flag):
  exactly-one challenger per W; unit ((0,1,2),3);
  --induced SIZES  for each candidate subset A with |A| in SIZES, some W inside A
                   picks a challenger outside A (needs the m=|A| theorem);
  --lex gen|full   lex-leader constraints for the stabilizer S_3 x S_4 of the
                   unit event (same encoding as search.py, for exact comparison);
  every S_8 image of every core, as "not all of these events".
"""
import argparse
import itertools as it
import json
import math
import sys
from fractions import Fraction

import numpy as np

# Every soundness check below is an explicit test, never a bare assert: python -O
# and PYTHONOPTIMIZE strip asserts, and the CNF depends only on the core supports,
# so a skipped weight check would still write the manifest-hash CNF.
if sys.flags.optimize:
    sys.exit('FAIL: gen.py refuses to run under python -O / PYTHONOPTIMIZE')


def die(msg):
    sys.exit(f'FAIL: {msg}')


M = 8
SETS = list(it.combinations(range(M), 3))
EVENTS = [(w, c) for w in SETS for c in range(M) if c not in w]
EID = {e: i for i, e in enumerate(EVENTS)}
if len(EVENTS) != 280:
    die('expected 280 events')


def event_truth():
    perms = np.array(list(it.permutations(range(M))), dtype=np.int8)
    pos = np.empty_like(perms)
    rows = np.arange(len(perms))[:, None]
    pos[rows, perms] = np.arange(M, dtype=np.int8)[None, :]
    truth = np.empty((len(EVENTS), len(perms)), dtype=bool)
    for i, (w, c) in enumerate(EVENTS):
        truth[i] = pos[:, c] < pos[:, list(w)].min(axis=1)
    return truth


def check_core(truth, core):
    y = {}
    for i, q in core:
        q = Fraction(q)
        if not q > 0:
            die(f'nonpositive weight {q} on event {i}')
        y[int(i)] = y.get(int(i), 0) + q
    if sum(y.values()) != 1:
        die(f'weights sum to {sum(y.values())}, not 1')
    den = math.lcm(*(q.denominator for q in y.values()))
    total = np.zeros(truth.shape[1], dtype=object)
    for i, q in y.items():
        total += int(q * den) * truth[i].astype(object)
    bound = Fraction(int(total.max()), den)
    return sorted(y), bound


def image(p, e):
    w, c = EVENTS[e]
    return EID[(tuple(sorted(p[x] for x in w)), p[c])]


def lex_clauses(kind, nvars):
    if kind == 'full':
        perms = [a + (3,) + b for a in it.permutations((0, 1, 2))
                 for b in it.permutations((4, 5, 6, 7)) if a + (3,) + b != tuple(range(M))]
    else:
        perms = []
        for u, v in list(it.combinations((0, 1, 2), 2)) + list(it.combinations((4, 5, 6, 7), 2)):
            p = list(range(M)); p[u], p[v] = p[v], p[u]
            perms.append(tuple(p))
    out = []
    for p in perms:
        prev = None
        for e in range(len(EVENTS)):
            f = image(p, e)
            if f == e:
                continue
            x, y = e + 1, f + 1
            g = [] if prev is None else [-prev]
            nvars += 1
            eq = nvars
            out += [g + [x, -y], g + [-x, -y, eq], g + [x, y, eq], [-eq, -x, y], [-eq, x, -y]]
            if prev is not None:
                out.append([-eq, prev])
            prev = eq
    return out, nvars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cores', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--induced', default='', help='comma list of subset sizes, e.g. 4,5,6,7')
    ap.add_argument('--lex', choices=['none', 'gen', 'full'], default='none')
    ap.add_argument('--no-unit', action='store_true')
    a = ap.parse_args()

    truth = event_truth()
    cores, worst, seen_support = [], Fraction(0), set()
    for path in a.cores:
        for core in json.load(open(path)):
            support, bound = check_core(truth, core)
            if not bound < Fraction(1, 2):
                die(f'not a core: bound {bound} >= 1/2 in {path}: {core}')
            worst = max(worst, bound)
            if tuple(support) not in seen_support:
                seen_support.add(tuple(support))
                cores.append(support)
    print(f'farkas: {len(cores)} distinct core supports valid over {truth.shape[1]} full rankings; worst bound {worst}')
    print(f'worst_bound={worst}')

    clauses = []
    for w in SETS:
        ch = [EID[(w, c)] + 1 for c in range(M) if c not in w]
        clauses.append(ch)
        clauses += [[-x, -y] for x, y in it.combinations(ch, 2)]
    if not a.no_unit:
        clauses.append([EID[((0, 1, 2), 3)] + 1])
    for size in [int(s) for s in a.induced.split(',') if s]:
        for sub in it.combinations(range(M), size):
            A = set(sub)
            clauses.append([EID[(w, c)] + 1 for w in SETS if set(w) <= A for c in range(M) if c not in A])
    nvars = len(EVENTS)
    if a.lex != 'none':
        extra, nvars = lex_clauses(a.lex, nvars)
        clauses += extra
    seen = set()
    for p in it.permutations(range(M)):
        mp = [image(p, e) for e in range(len(EVENTS))]
        for core in cores:
            img = tuple(sorted(mp[e] + 1 for e in core))
            if img not in seen:
                seen.add(img)
                clauses.append([-v for v in img])
    with open(a.out, 'w') as f:
        f.write(f'p cnf {nvars} {len(clauses)}\n')
        for cl in clauses:
            f.write(' '.join(map(str, cl)) + ' 0\n')
    print(f'orbit clauses {len(seen)}; wrote {a.out}: vars {nvars} clauses {len(clauses)}')


if __name__ == '__main__':
    sys.exit(main())
