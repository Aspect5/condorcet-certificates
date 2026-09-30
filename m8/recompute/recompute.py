#!/usr/bin/env python3
"""Independent, standard-library reconstruction of route A at 019da046.

Run in a no-network sandbox. The JSON source is copied from the pinned commit.
The script validates each rational core over all 8! rankings, generates the
base DIMACS in the reference ordering, and hashes the 21 covered cube inputs.
"""

import hashlib
import itertools
import json
import math
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "long-160f-all-cores.json"
BASE = ROOT / "A145-none.cnf"
SOURCE_SHA = "4fe9d02c36990847710b2d877fc3f674ebd755c974b3bbae1740b3a5efb441d2"
WINS = list(itertools.combinations(range(8), 3))
EVENTS = [(w, c) for w in WINS for c in range(8) if c not in w]
EID = {event: i + 1 for i, event in enumerate(EVENTS)}


def core_bound(core):
    weights = {}
    for number, rational in core:
        assert isinstance(number, int) and 0 <= number < 280
        value = Fraction(rational)
        assert value > 0
        weights[number] = weights.get(number, Fraction()) + value
    assert sum(weights.values()) == 1
    denominator = math.lcm(*(x.denominator for x in weights.values()))
    scaled = [(EVENTS[i], int(y * denominator)) for i, y in weights.items()]
    maximum = 0
    for ranking in itertools.permutations(range(8)):
        position = [0] * 8
        for place, candidate in enumerate(ranking):
            position[candidate] = place
        score = sum(weight for (w, c), weight in scaled
                    if position[c] < min(position[x] for x in w))
        maximum = max(maximum, score)
    result = Fraction(maximum, denominator)
    assert result < Fraction(1, 2), (core, result)
    return tuple(sorted(weights)), result


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_base(supports):
    body_path = ROOT / "A145-none.body.tmp"
    seen = set()
    clauses = 0
    with open(body_path, "wb") as out:
        def clause(literals):
            nonlocal clauses
            out.write((" ".join(map(str, literals)) + " 0\n").encode())
            clauses += 1

        for w in WINS:
            choices = [EID[(w, c)] for c in range(8) if c not in w]
            clause(choices)
            for pair in itertools.combinations(choices, 2):
                clause((-pair[0], -pair[1]))
        clause((EID[((0, 1, 2), 3)],))
        for permutation in itertools.permutations(range(8)):
            mapped = [EID[(tuple(sorted(permutation[x] for x in w)), permutation[c])]
                      for w, c in EVENTS]
            for support in supports:
                image = tuple(sorted(mapped[i] for i in support))
                if image not in seen:
                    seen.add(image)
                    clause((-x for x in image))
    assert len(seen) == 4_160_520
    assert clauses == 4_161_137
    with open(BASE, "wb") as out, open(body_path, "rb") as inp:
        out.write(f"p cnf 280 {clauses}\n".encode())
        for block in iter(lambda: inp.read(1 << 20), b""):
            out.write(block)
    body_path.unlink()
    return clauses, len(seen)


def leaf_hashes(clauses):
    body = BASE.read_bytes().split(b"\n", 1)[1]
    cubes = {"Lcube-456-3": [((4, 5, 6), 3)]}
    for first in (0, 1, 2):
        for second in (0, 1, 2, 3, 4):
            cubes[f"Lc456-{first}-567-{second}"] = [
                ((4, 5, 6), first), ((5, 6, 7), second)]
    for second in (0, 1, 2, 3, 6):
        cubes[f"Lc456-7-457-{second}"] = [
            ((4, 5, 6), 7), ((4, 5, 7), second)]
    assert len(cubes) == 21
    assert {cube[0][1] for cube in cubes.values()} == {0, 1, 2, 3, 7}
    assert all({cube[1][1] for cube in cubes.values() if len(cube) == 2
                and cube[0][1] == first} == ({0, 1, 2, 3, 6} if first == 7
                                          else {0, 1, 2, 3, 4})
               for first in (0, 1, 2, 7))
    results = {}
    for name, cube in cubes.items():
        units = b"".join(f"{EID[e]} 0\n".encode() for e in cube)
        digest = hashlib.sha256()
        digest.update(f"p cnf 280 {clauses + len(cube)}\n".encode())
        digest.update(body)
        digest.update(units)
        results[name] = {"sha256": digest.hexdigest(), "units": [EID[e] for e in cube]}
    return results


def main():
    assert sha(SOURCE) == SOURCE_SHA
    raw = json.loads(SOURCE.read_text())
    supports, seen, worst = [], set(), Fraction()
    for core in raw:
        support, bound = core_bound(core)
        worst = max(worst, bound)
        if support not in seen:
            seen.add(support)
            supports.append(support)
    assert len(raw) == 160 and len(supports) == 145
    clauses, orbit_clauses = write_base(supports)
    result = {
        "source_sha256": sha(SOURCE), "source_cores": len(raw),
        "distinct_supports": len(supports), "rankings_checked_per_core": 40320,
        "worst_core_bound": str(worst), "variables": 280,
        "clauses": clauses, "orbit_clauses": orbit_clauses,
        "base_sha256": sha(BASE), "leaves": leaf_hashes(clauses),
    }
    (ROOT / "recompute.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "leaves"}, indent=2))


if __name__ == "__main__":
    main()
