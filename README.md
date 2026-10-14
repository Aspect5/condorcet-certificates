# Size-3 Condorcet winning sets for 7 and 8 candidates: exact certificates

Institute for Recursive Self Improvement (IRSI), 2026-09-29.
Status: verified by an independent recomputation and by a formally verified LRAT
checker (cake_lpr). Not peer reviewed.

## Claims

Setting: n voters, each with a strict ranking of m candidates. A set W of
candidates is a *Condorcet winning set* if for every candidate c outside W,
fewer than n/2 voters rank c above every member of W (equivalently, a strict
majority prefers some member of W to c). A tie at exactly n/2 counts against W.
This is the definition of Elkind, Lang and Saffidine (2015), Charikar et al.
(2025) and the Epoch AI open problem "Condorcet winning sets".

1. **m = 8.** Every election with 8 candidates and any number of voters has a
   Condorcet winning set of size 3.
2. **m = 7.** The same holds for 7 candidates (implied by claim 1 by adding a
   candidate ranked last by everyone, and certified separately and much more
   cheaply).

So a counterexample to the conjecture of Charikar et al. that size 3 always
suffices needs at least 9 candidates.

What is new. For odd n both claims follow from Elkind, Lang and Saffidine
(2015), Corollary 1, which gives size 3 for odd n up to m = 14 and for all n up
to m = 6. For even n at m = 7 that corollary gives only size 4, but size 3
follows from the proof of their Proposition 4 together with the fact that every
tournament on 6 vertices has a dominating set of size 2 (Erdos 1963); the m = 7
certificate here is an independent exact check of that case. For m = 8 (and
all m <= 8, k >= 3), version 2 of Zilberstein, Martins and Berker
(arXiv:2604.19851v2, "MILP the Gap", posted 2026-10-10) states that every
election admits a Condorcet winning set, independent of the number of voters,
from a floating-point mixed-integer program (Gurobi). This repository does not
claim to be first with that statement. What it adds is an exact, independently
checkable proof: SAT certificates checked by the formally verified cake_lpr
checker and exact rational cores, timestamped in Bitcoin on 2026-09-29 (see
below), before version 2 was posted. Version 1 of that paper (April 2026) gave
only a floating-point bound for m = 7 and no m = 8, k = 3 bound below 1/2.

## Method

Suppose an election has no Condorcet winning set of size 3. Then every 3-set W
has a challenger c ranked above all of W by at least half the voters. Encode the
choice of challenger as 280 Boolean variables (W, c) for m = 8 (140 for m = 7),
exactly one per W, and fix one challenger by symmetry. A *core* is a set of
events (W, c) with positive rational weights summing to 1 such that every single
ranking satisfies events of total weight below 1/2; no election can then satisfy
all events of a core at level 1/2. Each core is checked exactly over all m!
rankings. Adding "not all of these" for every relabeling of every core gives a
CNF formula that is satisfiable if a counterexample exists.

- m = 8: 145 distinct cores (worst bound 9/19), 4,161,137 clauses, split into 21
  cubes; CaDiCaL 3.0.1 proves each cube unsatisfiable and writes an LRAT proof
  (5.05 GB zstd in total); cake_lpr verifies all 21. `cover.py` checks that the
  cubes cover every case. The argument is self-contained: it does not use the
  m <= 6 theorem or the m = 7 certificate. Full argument: `m8/cert/CERT.md`.
- m = 7: 9 cores (worst bound 2/5), 22,226 clauses, one LRAT proof (55 MB xz),
  verified by cake_lpr, drat-trim and lrat-check.

Trusted base: the CNF generators (about 150 lines of Python, event indexing and
relabeling) and cake_lpr. Each generator was written twice, independently: for
m = 8 the two write byte-identical CNFs (`m8/recompute/`), for m = 7 they write
the same clause set (`m7/recompute/`). There is no Lean statement of the encoding.

## Verify

```
./verify.sh            # everything: about 25 CPU-minutes, 32 GiB machine, 5.1 GB download
./verify.sh --quick    # hashes and CNF regeneration only, a few minutes
```

`verify.sh` checks `MANIFEST.sha256`, builds cake_lpr from the pinned upstream
commit, regenerates every CNF from the cores (rechecking each core exactly),
compares CNF hashes, downloads any missing proof from the GitHub release and
checks its hash, runs cake_lpr on every proof and requires `s VERIFIED UNSAT`,
then runs `cover.py`. Needs python3 with numpy, gcc, git, curl, zstd and xz.

Memory: the default `CAKE_HEAP_MB=26000` is the setting of all the authors' full
runs. The independent recomputation ran every m = 8 proof under a hard 28 GiB
memory cap, with 25.4 GiB peak RSS (`m8/recompute/README.md`). Use a machine with
at least 32 GiB and keep other large jobs off it; a larger `CAKE_HEAP_MB` needs
more memory, not less.

What `verify.sh` enforces: it drops `PYTHONOPTIMIZE` (with a note) and refuses
a `PYTHON` that still runs with `-O`, and the generators refuse `-O` on their
own; none of their checks are Python `assert`s; it requires the generators to print `worst_bound=2/5` (m = 7)
and `worst_bound=9/19` (m = 8); it prints `sha256(MANIFEST.sha256)` and fails
unless it equals the timestamped
`ae319c72fe646532c836856be0f86572b8c92d10b84c6de9050815d572c77555`; and it fails
on any manifest entry that is missing and is neither a regenerated CNF nor a
proof. The scripts hardened after the timestamp are listed with their new hashes
in `MANIFEST.post-stamp.sha256`; `verify.sh` names each one it checks against
that file instead of the anchored manifest. The cores, CNFs and proofs are
unchanged and still match the anchored manifest.

`MANIFEST.sha256` lists every file of the certificate, including the CNFs (which
`verify.sh` regenerates) and the proofs. Its OpenTimestamps file
`MANIFEST.sha256.ots` anchors the manifest's hash in Bitcoin block 969212
(2026-09-29 22:18:32 UTC), which proves the manifest existed by that block's
time; matching hashes tie the proofs and CNFs to that manifest. Check it with
`ots verify MANIFEST.sha256.ots` (pip install opentimestamps-client; this needs
a Bitcoin node, or run `ots --no-bitcoin verify MANIFEST.sha256.ots` and compare
the merkle root it prints with the block's).

`stamp-2026-09-29T2114Z/` keeps the first manifest and its OpenTimestamps file,
which anchors that manifest's hash in Bitcoin block 969208 (2026-09-29 21:42:56
UTC). It predates corrections to three documentation files listed in it; its
proof and CNF hashes are identical to the current manifest's. Check it with
`cd stamp-2026-09-29T2114Z && ots verify MANIFEST.sha256.ots`.

## Files

| path | what |
|---|---|
| `m8/cert/gen.py`, `mkcube.py`, `cover.py`, `control.py` | CNF generator with exact core check, cube writer, cube coverage check, random-profile control |
| `m8/cert/long-160f-all-cores.json` | the rational cores for m = 8 |
| `m8/cert/CERT.md`, `LEAVES.tsv`, `CNF-HASHES.txt` | soundness argument, per-cube hashes and timings |
| `m8/recompute/` | independent second generator and its outputs |
| `m7/mkcnf.py`, `m7/m7k3.json` | m = 7 generator and cores |
| `m7/recompute/` | independent m = 7 recomputation |
| release assets | 21 `*.lrat.zst` (m = 8) and `m7k3.lrat.xz` (m = 7) |
| `stamp-2026-09-29T2114Z/` | first manifest and its OpenTimestamps file |

## How this was produced

The certificates were found, built and checked by AI agents at IRSI (Anthropic
Claude and OpenAI Codex models) under the direction of Peter Seelman. The m = 8
certificate was built by one agent and recomputed by another, from a different
provider, with its own generator. The m = 7 certificate was built, recomputed
and proof-checked by three separate agents. A human has not checked the proofs
by hand; the evidence is the verified checker output that `verify.sh` reproduces.

## Credit and references

- E. Elkind, J. Lang, A. Saffidine. Condorcet winning sets. Social Choice and
  Welfare 44 (2015) 493-517, doi:10.1007/s00355-014-0853-4. Defines the
  problem; Corollary 1 settles odd n.
- M. Charikar, A. Lassota, P. Ramakrishnan, A. Vetta, K. Wang. Six candidates
  suffice to win a voter majority. STOC 2025, arXiv:2411.03390. Conjectures size 3.
- I. Zilberstein, R. Martins, R. E. Berker. MILP the Gap: An Automated
  Reasoning Approach to Condorcet's Paradox. arXiv:2604.19851v2 (2026-10-10).
  Floating-point MILP result for all m <= 8, k >= 3.
- I. Zilberstein, R. E. Berker, Y. Li, R. Martins. Is Four Enough? Automated
  Reasoning Approaches and Dual Bounds for Condorcet Dimensions of Elections.
  arXiv:2604.19851 (GAIW 2026). MILP bounds for small m, including the
  floating-point m = 7 bound.
- P. Erdos. On a problem in graph theory. Math. Gazette 47 (1963) 220-223.
  Every 6-vertex tournament has a dominating set of size 2; with ELS15
  Proposition 4 this gives size 3 for m = 7, even n.
- Y. K. Tan, M. J. H. Heule, M. O. Myreen. Verified propagation redundancy and
  compositional UNSAT checking in CakeML (2023); the cake_lpr checker,
  https://github.com/tanyongkiam/cake_lpr.
- CaDiCaL SAT solver, A. Biere et al.

Contact: peter@irsi.ai
