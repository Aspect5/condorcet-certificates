#!/usr/bin/env python3
"""Cube-split bookkeeping for the self-contained certificate.

usage: cover.py BASE.cnf RUNS_DIR LEAF.cnf ...
Checks (1) each leaf CNF is BASE plus only positive unit clauses (the cube),
(2) the cubes cover every assignment allowed by BASE's at-least-one clauses
(branching on a 3-set's five challengers is complete by exactly-one),
(3) each leaf has a cake_lpr 's VERIFIED UNSAT' check whose recorded CNF sha256
matches the leaf file. Prints COVERED/NOT COVERED and the per-leaf status.
"""
import hashlib
import itertools as it
import os
import sys

M = 8
SETS = list(it.combinations(range(M), 3))
EVENTS = [(w, c) for w in SETS for c in range(M) if c not in w]

base, runs, leaves = sys.argv[1], sys.argv[2], sys.argv[3:]
with open(base, 'rb') as f:
    bhead, bbody = f.read().split(b'\n', 1)
bv, bc = map(int, bhead.split()[2:])


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 24), b''):
            h.update(block)
    return h.hexdigest()


cubes, ok = [], True
for leaf in leaves:
    with open(leaf, 'rb') as f:
        head, body = f.read().split(b'\n', 1)
    assert body.startswith(bbody), f'{leaf}: body does not extend base'
    extra = [l for l in body[len(bbody):].decode().split('\n') if l]
    units = [int(l.split()[0]) for l in extra]
    assert all(len(l.split()) == 2 and l.split()[1] == '0' and 0 < u <= 280 for l, u in zip(extra, units))
    v, c = map(int, head.split()[2:])
    assert v == bv and c == bc + len(units), f'{leaf}: header mismatch'
    cube = {EVENTS[u - 1][0]: EVENTS[u - 1][1] for u in units}
    assert len(cube) == len(units), f'{leaf}: two units on one 3-set'
    cubes.append(cube)
    rest = os.path.basename(leaf)[:-4].replace('A145-none-c456-', '', 1)
    tag = ('Lc456-' if '-' in rest else 'Lcube-456-') + rest
    chk = os.path.join(runs, tag + '.check')
    status = 'NO CHECK'
    if os.path.exists(chk):
        text = open(chk).read()
        good = 's VERIFIED UNSAT' in text and f'cnf_sha256={sha(leaf)}' in text
        status = 'VERIFIED' if good else 'CHECK FAILED'
    ok &= status == 'VERIFIED'
    print(f'{tag}: cube {sorted(cube.items())} -> {status}')


alo = set()
for line in bbody.decode().split('\n'):
    lits = line.split()[:-1]
    if lits and all(not t.startswith('-') for t in lits):
        alo.add(frozenset(int(t) for t in lits))


def branch_ok(w):
    need = frozenset(EVENTS.index((w, c)) + 1 for c in range(M) if c not in w)
    assert need in alo, f'base lacks the at-least-one clause for {w}'
    return True


def covers(active, fixed):
    if any(all(fixed.get(w) == c for w, c in cube.items()) for cube in active):
        return True
    for cube in active:
        for w in cube:
            if w not in fixed:
                branch_ok(w)
                return all(covers([q for q in active if q.get(w, c) == c], {**fixed, w: c})
                           for c in range(M) if c not in w)
    return False


cov = covers(cubes, {})
print('COVERED' if cov else 'NOT COVERED', '| all leaves verified' if ok else '| some leaves unverified')
