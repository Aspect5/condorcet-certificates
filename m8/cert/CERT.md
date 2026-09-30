# m = 8, k = 3: certificate layout and soundness argument

Status: Independently recomputed and LRAT-checked; not peer reviewed.

## Result (OBSERVED, 2026-09-29 16:40 UTC)
- Route A (self-contained; no induced-subset clauses, no lex-leader): base CNF `A145-none.cnf` (280 vars, 4,161,137 clauses, sha256 `348efbbb...44cc`) = exactly-one per W + unit ((0,1,2),3) + all S_8 images of 145 exactly checked cores. Split into 21 cubes: challenger of {4,5,6} in {0,1,2,3,7}; cubes 0, 1, 2 refined on the challenger of {5,6,7}, cube 7 on the challenger of {4,5,7}. Every leaf CNF: CaDiCaL 3.0.1 `--lrat` (seed 1) UNSAT, binary LRAT (zstd), **cake_lpr `s VERIFIED UNSAT`**. `cover.py` confirms each leaf is the base plus only its cube units, the base holds the at-least-one clause of every branching 3-set, the cubes cover all assignments, and each check log names the leaf's sha256. Output: `COVERED | all leaves verified`. Per-leaf hashes, times and proof sizes: `LEAVES.tsv` (solve 60,948 s total, proofs 5.05 GB zstd, checks 1,356 s, peak RSS 41 GB).
- Route B (codex CNF long-160f, with induced clauses 4..7 and full lex): CaDiCaL `--lrat` seed 43 UNSAT in 6,926 s; long-123f seed 41 UNSAT in 7,301 s. **cake_lpr `s VERIFIED UNSAT` for both** (160f: 99 s, proof zst sha256 `70d9b278...bde1`; 123f: 122 s, `27b7ad49...3f06`). Route B also rests on step 4 (ELS 2015 for m <= 6, the lab's m = 7 certificate) and step 5.
- Route C (A145-lex: self-contained with full lex, no induced): plain CaDiCaL seed 2 UNSAT in 6,833 s; LRAT rerun pending.
- Proof files: `m8/proofs/<leaf>.lrat.zst` (release assets). The reproduction block below shows how they were produced.

## Reproduce route A
```
python3 gen.py long-160f-all-cores.json --out A145-none.cnf          # sha256 348efbbb...44cc
python3 mkcube.py A145-none.cnf A145-none-c456 '4,5,6:*'                           # use leaf -3; -0,-1,-2,-7 are refined:
python3 mkcube.py A145-none.cnf A145-none-c456-0 '4,5,6:0' '5,6,7:*'               # likewise -1, -2
python3 mkcube.py A145-none.cnf A145-none-c456-7 '4,5,6:7' '4,5,7:*'
cadical --lrat --seed=1 LEAF.cnf LEAF.lrat; cake_lpr --CML_HEAP_SIZE=40000 --CML_STACK_SIZE=4000 LEAF.cnf LEAF.lrat
python3 cover.py A145-none.cnf RUNS A145-none-c456-3.cnf A145-none-c456-[0127]-*.cnf
```
Note: the top-level split files from `mkcube.py ... '4,5,6:*'` are named `A145-none-c456-456-<c>.cnf`; the run used `A145-none-c456-3.cnf` with identical content (base + unit ((4,5,6),3)).

## Claim
Every election with 8 candidates and any number n of voters (strict rankings) has a Condorcet winning set of size 3 under Epoch's rule: a 3-set W is overthrown iff some c outside W is ranked above all of W by at least n/2 voters. Equivalently: no 8-candidate counterexample to the Charikar et al. size-3 conjecture exists, for odd or even n.

## Objects
- Events (W, c), W a 3-subset of {0..7}, c not in W: 280 variables, ordered as `combinations(range(8),3)` x ascending c (variable = index + 1).
- Core: event set C with rational weights y > 0, sum 1, such that max over all 8! rankings r of sum_{e in C} y_e [r makes e true] < 1/2. Checked by `gen.py` with exact integers over all 40,320 full rankings.
- CNF variants (all written by `gen.py`; hashes in `CNF-HASHES.txt`):

| CNF | exactly-one per W | unit ((0,1,2),3) | induced-subset clauses | lex-leader | core supports |
|---|---|---|---|---|---:|
| A145-none | yes | yes | none | none | 145 |
| A145-lex | yes | yes | none | full S_3 x S_4 | 145 |
| A145-lexgen | yes | yes | none | transpositions | 145 |
| A145-i7lex | yes | yes | size 7 | full | 145 |
| long-160f (codex) | yes | yes | sizes 4..7 | full | 145 |
| long-123f (codex) | yes | yes | sizes 4..7 | full | 108 |

## Soundness (CNF UNSAT implies the claim)
1. Suppose an election with no winning 3-set. Let x be its voter distribution. Each W has some c with x-mass of "c above W" >= 1/2 (ties at n/2 included, any n).
2. Relabel so that 3 overthrows {0,1,2} (relabeling preserves the property). Choose one overthrower f(W) per W with f({0,1,2}) = 3. Setting exactly the events (W, f(W)) true satisfies exactly-one and the unit clause.
3. Core images: if all events of p(C) had mass >= 1/2 under x, the relabeled distribution would give every event of C mass >= 1/2, so sum y_e mass_e >= 1/2; but that sum is an average over rankings of values each < 1/2. So every orbit clause holds.
4. Induced-subset clause for A (|A| = j): if every W inside A chose f(W) inside A, the election restricted to A (j candidates) would have no winning 3-set. For j <= 6 this contradicts Elkind, Lang, Saffidine 2015, Cor. 1 (dim <= g(m)+1 = 3 for even n, g(m) = 2 for odd n, m <= 6); for j = 7 it contradicts the LRAT-checked m = 7 certificate (`m7/` in this bundle). Variants A145-none/-lex/-lexgen do not use this step.
5. Lex-leader (variants with lex): the clause set of steps 2-4 is invariant under the stabilizer H = S_3 x S_4 of the unit event (core orbits are closed under S_8; exactly-one and induced clauses are S_8-invariant). If some assignment satisfies them, the lexicographically maximal assignment in its H-orbit does too, and it satisfies x >=_lex x∘p for every p in H (or every listed generator), with the auxiliary prefix-equality variables set to their true values. So adding the lex-leader clauses preserves satisfiability.
6. Hence a satisfying assignment exists; UNSAT (checked by cake_lpr) refutes step 1.

## Trust base
- Python: `gen.py` (event indexing, S_8 action, exact Farkas check, clause writing). It regenerates the codex CNFs byte-identically from the same core lists, i.e. two independently written generators agree.
- cake_lpr (formally verified LRAT checker, CakeML), pinned as in the m = 7 check.
- Route A uses only steps 1-3 and 6, plus the case split: the at-least-one clause of a 3-set makes its five challenger cubes exhaustive (checked by `cover.py`).
- Step 4 only for variants with induced clauses: a published theorem (m <= 6) and the lab's m = 7 certificate.

## Controls
- `control.py A145-none.cnf 300 1`: 300 random integer profiles (1..16 distinct ranking types); no core clause is ever fully held; best observed 50/56 overthrown. Negative control: a planted invalid 3-event clause is flagged.
