#!/usr/bin/env python3
"""Independent ranking-simplex search for Condorcet winning-set counterexamples.

No imports, data, or certificates from condorcet-winning-sets are used here.
For each k-set W, one challenger c must have probability of topping W+c at
least 1/2. A leaf is an LP over the simplex of ranking prefixes. Infeasible
leaves get rational Farkas certificates reconstructed from a dual LP.
"""
import argparse
import itertools
import json
import site
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix

# The allowed exact-work environment has PySAT in the user site.  This science
# environment supplies SciPy; append the existing site without installing.
sys.path.append(site.getusersitepackages())
from pysat.solvers import Cadical195, Glucose3


def instance(m, k):
    sets = list(itertools.combinations(range(m), k))
    events = [(w, c) for w in sets for c in range(m) if c not in w]
    prefixes = list(itertools.permutations(range(m), m-k))
    rows, cols = [], []
    for j, p in enumerate(prefixes):
        rank = {c: i for i, c in enumerate(p)}
        for i, (w, c) in enumerate(events):
            if c in rank and all(rank[c] < rank.get(a, m) for a in w):
                rows.append(i); cols.append(j)
    a = csr_matrix((np.ones(len(rows), dtype=np.float64), (rows, cols)),
                   shape=(len(events), len(prefixes)))
    return sets, events, prefixes, a


def exact_dual(a, selected):
    """Find y>=0, sum y=1, max_column sum(y_i A_ij)<1/2."""
    b = a[selected].tocsc()
    n = len(selected)
    obj = np.zeros(n+1); obj[-1] = 1
    mat = np.hstack([b.T.toarray(), -np.ones((a.shape[1], 1))])
    sol = linprog(obj, A_ub=mat, b_ub=np.zeros(a.shape[1]),
                  A_eq=np.array([[1.0]*n+[0.0]]), b_eq=[1.0],
                  bounds=[(0, None)]*n+[(None, None)], method='highs')
    if not sol.success or sol.fun >= 0.5-1e-8:
        return None
    for lim in (1000, 1000000, 1000000000):
        y = [Fraction(float(v)).limit_denominator(lim) for v in sol.x[:n]]
        ysum = sum(y)
        if not ysum:
            continue
        sparse = [(selected[i], y[i]/ysum) for i in range(n) if y[i]]
        bound = max(sum(q for e, q in sparse if a[e, j]) for j in range(a.shape[1]))
        if bound < Fraction(1, 2):
            return sparse, bound
    return None


def minimize_core(a, weights):
    """Delete redundant selected inequalities before learning an orbit clause."""
    core = [i for i,_ in weights]
    for event in list(core):
        trial = [i for i in core if i != event]
        if not trial:
            continue
        sol = linprog(np.zeros(a.shape[1]), A_ub=-a[trial],
                      b_ub=np.full(len(trial), -0.5),
                      A_eq=np.ones((1,a.shape[1])), b_eq=[1.0],
                      bounds=(0,None), method='highs')
        if sol.status == 2:
            core = trial
    ans = exact_dual(a, core)
    return ans if ans is not None else (weights, None)


def check_dual(a, cert):
    y = [(int(i), Fraction(s)) for i, s in cert['weights']]
    assert all(0 <= i < a.shape[0] and q >= 0 for i, q in y)
    assert sum(q for _, q in y) == 1
    bound = max(sum(q for i, q in y if a[i, j]) for j in range(a.shape[1]))
    assert bound < Fraction(1, 2), bound
    assert str(bound) == cert['bound']
    return str(bound)


def search(m, k, output, max_nodes=10000):
    sets, events, prefixes, a = instance(m, k)
    by_set = [[i for i, (v, _) in enumerate(events) if v == w] for w in sets]
    # Relabeling sends an arbitrary first witness to (0,...,k-1) challenged by k.
    order = sorted(range(len(sets)), key=lambda i: (-len(set(sets[i]) & set(sets[0])), sets[i]))
    assert order[0] == 0
    clauses = []
    leaves = []
    nodes = 0
    started = time.monotonic()

    def dfs(chosen):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            return 'limit'
        picked = set(chosen)
        if any(core <= picked for core in clauses):
            return 'unsat'
        selected = sorted(chosen)
        sol = linprog(np.zeros(a.shape[1]), A_ub=-a[selected],
                      b_ub=np.full(len(selected), -0.5),
                      A_eq=np.ones((1, a.shape[1])), b_eq=[1.0],
                      bounds=(0, None), method='highs')
        if sol.status == 2:
            dual = exact_dual(a, selected)
            if dual is None:
                return 'uncertified'
            weights, bound = dual
            core = frozenset(i for i, _ in weights)
            clauses.append(core)
            leaves.append({'weights': [[i, str(q)] for i, q in weights],
                           'bound': str(bound)})
            return 'unsat'
        if not sol.success:
            return 'solver-error'
        if len(chosen) == len(sets):
            vals = [Fraction(float(v)).limit_denominator(1000000) for v in sol.x]
            total = sum(vals)
            x = [[list(prefixes[j]), str(v/total)]
                 for j, v in enumerate(vals) if v]
            return ('sat', x, sorted(chosen))
        wi = order[len(chosen)]
        for event in (by_set[wi][:1] if not chosen else by_set[wi]):
            ans = dfs(chosen + [event])
            if ans != 'unsat':
                return ans
        return 'unsat'

    verdict = dfs([])
    record = {'m': m, 'k': k, 'status': verdict[0] if isinstance(verdict, tuple) else verdict,
              'nodes': nodes, 'seconds': time.monotonic()-started,
              'event_count': len(events), 'prefix_count': len(prefixes),
              'dual_leaves': leaves}
    if isinstance(verdict, tuple):
        record['profile'] = verdict[1]
        record['chosen'] = verdict[2]
    Path(output).write_text(json.dumps(record, separators=(',', ':')))
    return record


def cegar(m, k, output, max_nodes=100000):
    sets, events, prefixes, a = instance(m, k)
    event_id = {e: i for i, e in enumerate(events)}
    relabelings = [tuple(event_id[(tuple(sorted(p[x] for x in w)), p[c])]
                         for w,c in events)
                   for p in itertools.permutations(range(m))]
    by_set = [[i for i, (v, _) in enumerate(events) if v == w] for w in sets]
    started = time.monotonic()
    leaves = []
    solver = Cadical195()
    for choices in by_set:
        solver.add_clause([i+1 for i in choices])
        for u, v in itertools.combinations(choices, 2):
            solver.add_clause([-(u+1), -(v+1)])
    solver.add_clause([by_set[0][0]+1])
    seen_images = set()
    status = 'limit'
    profile = None
    for iteration in range(max_nodes):
        if not solver.solve():
            status = 'unsat'; break
        model = solver.get_model()
        picked = sorted(v-1 for v in model if 1 <= v <= len(events) and v > 0)
        sol = linprog(np.zeros(a.shape[1]), A_ub=-a[picked],
                      b_ub=np.full(len(picked), -0.5),
                      A_eq=np.ones((1, a.shape[1])), b_eq=[1.0],
                      bounds=(0, None), method='highs')
        if sol.success:
            status = 'sat'
            vals = [Fraction(float(v)).limit_denominator(1000000) for v in sol.x]
            total = sum(vals)
            vals = [v/total for v in vals]
            profile = [[list(prefixes[j]), str(v)] for j,v in enumerate(vals) if v]
            break
        if sol.status != 2:
            status = 'solver-error'; break
        dual = exact_dual(a, picked)
        if dual is None:
            status = 'uncertified'; break
        weights, bound = minimize_core(a, dual[0])
        if bound is None:
            weights, bound = dual
        core = tuple(i for i,_ in weights)
        leaves.append({'weights': [[i, str(q)] for i, q in weights], 'bound': str(bound)})
        for image in relabelings:
            moved = tuple(sorted(image[i] for i in core))
            if moved not in seen_images:
                seen_images.add(moved)
                solver.add_clause([-(i+1) for i in moved])
        if (iteration+1) % 10 == 0:
            print(f'iteration={iteration+1} clauses={len(seen_images)} elapsed={time.monotonic()-started:.1f}s', flush=True)
    record = {'m':m, 'k':k, 'status':status, 'nodes':len(leaves),
              'seconds':time.monotonic()-started, 'event_count':len(events),
              'prefix_count':len(prefixes), 'dual_leaves':leaves if status == 'unsat' else [], 'orbit':True,
              'image_clauses':len(seen_images)}
    if profile is not None:
        record['profile'] = profile
    Path(output).write_text(json.dumps(record,separators=(',',':')))
    solver.delete()
    return record


def verify(path, sat_solver='cadical'):
    data = json.loads(Path(path).read_text())
    sets, events, prefixes, a = instance(data['m'], data['k'])
    for leaf in data['dual_leaves']:
        check_dual(a, leaf)
    if data['status'] == 'sat':
        probs = [Fraction(0)]*len(prefixes)
        lookup = {p: j for j, p in enumerate(prefixes)}
        for p, q in data['profile']:
            probs[lookup[tuple(p)]] += Fraction(q)
        assert sum(probs) == 1
        for w in sets:
            assert any(sum(probs[j] for j in range(len(prefixes)) if a[i,j]) >= Fraction(1,2)
                       for i, (v,c) in enumerate(events) if v == w)
    elif data['status'] == 'unsat':
        # The finite clause system states that every W chooses one challenger.
        # Each verified dual excludes one impossible conjunction of choices.
        cores = [frozenset(int(i) for i, _ in leaf['weights']) for leaf in data['dual_leaves']]
        event_id = {e:i for i,e in enumerate(events)}
        by_set = [[i for i,(v,_) in enumerate(events) if v == w] for w in sets]
        solver_type = Cadical195 if sat_solver == 'cadical' else Glucose3
        with solver_type() as solver:
            for choices in by_set:
                solver.add_clause([i+1 for i in choices])
                for u,v in itertools.combinations(choices, 2):
                    solver.add_clause([-(u+1),-(v+1)])
            solver.add_clause([by_set[0][0]+1])
            if data.get('orbit'):
                for p in itertools.permutations(range(data['m'])):
                    mapping = [event_id[(tuple(sorted(p[x] for x in w)),p[c])]
                               for w,c in events]
                    for core in cores:
                        solver.add_clause([-(mapping[i]+1) for i in core])
            else:
                for core in cores:
                    solver.add_clause([-(i+1) for i in core])
            assert not solver.solve()
    else:
        raise ValueError('incomplete certificate')
    print(f"CHECKED {path}: {data['status']}; {len(data['dual_leaves'])} dual leaves")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run'); run.add_argument('m', type=int); run.add_argument('k', type=int)
    run.add_argument('output'); run.add_argument('--max-nodes', type=int, default=10000)
    ceg = sub.add_parser('cegar'); ceg.add_argument('m', type=int); ceg.add_argument('k', type=int)
    ceg.add_argument('output'); ceg.add_argument('--max-nodes', type=int, default=100000)
    chk = sub.add_parser('check'); chk.add_argument('path')
    chk.add_argument('--sat-solver', choices=('cadical','glucose'), default='cadical')
    args = ap.parse_args()
    if args.command in ('run','cegar'):
        info = (search if args.command == 'run' else cegar)(args.m, args.k, args.output, args.max_nodes)
        print({key: info[key] for key in ('m','k','status','nodes','seconds')})
    else:
        verify(args.path, args.sat_solver)
