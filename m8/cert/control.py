#!/usr/bin/env python3
"""Soundness control for the core clauses of a CNF, without the Farkas argument.

For random rational profiles x (mixtures of 1..16 random rankings with random
integer voter counts), take E(x) = events (W, c) with at least half the voters
putting c above all of W (exact integer counts). A sound core clause
"not all of these events" must never have all its events in E(x). Also reports,
per profile, how many of the 56 three-sets are overthrown. usage:
control.py CNF N SEED
"""
import itertools as it
import random
import sys

import numpy as np

M = 8
SETS = list(it.combinations(range(M), 3))
EVENTS = [(w, c) for w in SETS for c in range(M) if c not in w]

cnf, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rng = random.Random(seed)
core_clauses = []
with open(cnf) as f:
    for line in f:
        if line[0] in 'pc':
            continue
        lits = [int(t) for t in line.split()[:-1]]
        if len(lits) >= 3 and all(-280 <= v < 0 for v in lits):
            core_clauses.append([-v - 1 for v in lits])
lens = np.array([len(c) for c in core_clauses])
flat = np.concatenate([np.array(c) for c in core_clauses])
starts = np.concatenate([[0], np.cumsum(lens)[:-1]])
print(f'{len(core_clauses)} core clauses', flush=True)

worst, best_over = 0, 0
for t in range(n):
    k = rng.randint(1, 16)
    rankings = [rng.sample(range(M), M) for _ in range(k)]
    votes = [rng.randint(1, 9) for _ in range(k)]
    total = sum(votes)
    hold = np.zeros(len(EVENTS), dtype=bool)
    for i, (w, c) in enumerate(EVENTS):
        cnt = sum(v for r, v in zip(rankings, votes) if all(r.index(c) < r.index(a) for a in w))
        hold[i] = 2 * cnt >= total
    over = sum(any(hold[i] for i, (w, c) in enumerate(EVENTS) if w == s) for s in SETS)
    best_over = max(best_over, over)
    sat = np.add.reduceat(hold[flat].astype(np.int32), starts)
    full = int((sat == lens).sum())
    worst = max(worst, full)
    if full:
        print(f'VIOLATION profile {t}: {full} core clauses fully held', flush=True)
print(f'profiles {n}; violated core clauses max {worst}; most 3-sets overthrown {best_over}/56')
