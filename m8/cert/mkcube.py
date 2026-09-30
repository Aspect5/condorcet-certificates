#!/usr/bin/env python3
"""Write leaf CNFs = BASE + positive unit clauses. usage: mkcube.py BASE PREFIX 'a,b,c:x' ... 'W:*'
Each fixed spec 'a,b,c:x' adds event ((a,b,c),x); one trailing 'a,b,c:*' spec splits on all
five challengers of that 3-set. Output: PREFIX-<x...>.cnf per leaf."""
import itertools as it, sys
M = 8
SETS = list(it.combinations(range(M), 3))
EID = {e: i for i, e in enumerate((w, c) for w in SETS for c in range(M) if c not in w)}
base, prefix, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
head, body = open(base).read().split('\n', 1)
nv, nc = map(int, head.split()[2:])
fixed = []
for s in specs[:-1]:
    w, c = s.split(':'); fixed.append((tuple(map(int, w.split(','))), int(c)))
w, star = specs[-1].split(':'); w = tuple(map(int, w.split(','))); assert star == '*'
for c in [x for x in range(M) if x not in w]:
    units = fixed + [(w, c)]
    name = f"{prefix}-{''.join(map(str, w))}-{c}.cnf"
    with open(name, 'w') as f:
        f.write(f'p cnf {nv} {nc + len(units)}\n'); f.write(body)
        f.write(''.join(f'{EID[e] + 1} 0\n' for e in units))
    print(name)
