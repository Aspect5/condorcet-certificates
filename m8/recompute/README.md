# Independent route A recompute (candidate evidence)

Source: `lane/condorcet-m8` at `019da046`. The copied
`long-160f-all-cores.json` is the exact 11,309-byte artifact from that commit
(SHA-256 `4fe9d02c36990847710b2d877fc3f674ebd755c974b3bbae1740b3a5efb441d2`).
`recompute.py` is separate standard-library code. It checks every rational core
on all 40,320 strict rankings, removes duplicate supports, writes exactly-one
and unit clauses, then enumerates all S8 images in the pinned order. It also
hashes the 21 base-plus-cube-unit CNFs and checks that the branches cover all
five challengers of each split. It ran inside a Docker cloud sandbox with
`deny-all` egress policy. `recompute.json` is its output. `verify_inputs.py`
compared that output against the target TSV and SHA-256 values of on-disk
CNFs and compressed proofs, in the same sandbox.

`cake_lpr` was built inside this clone with `make cake_lpr` from
`tanyongkiam/cake_lpr` commit `a36874a8b750b43fe4b385b8ddbf5b033e46a3fa`
(the pinned local source snapshot). Input source hashes: `basis_ffi.c`
`8e30d84fdcb2177aa5571d7fa6661a2fae5ecfd56baa0ce49c65f9233a9f87cb`,
`cake_lpr.S` `2f3af32d55083839b3fa0e693afd817679c0b8944bef41def05a8b0ec72b7d4a`.
Build command: `gcc -O2 basis_ffi.c cake_lpr.S -o cake_lpr -std=c99`.
Built checker SHA-256: `1822ca1e5d0f925e8f3b73047941a8261bee65eef6ccb0e33bb49f92821a09ca`.
`check_proofs.sh` streams each compressed proof to this checker and retains
the separate per-leaf verdicts in `checks/`. A control using the bundled
`example.cnf` and an empty proof printed `c empty clause not derived at end of
proof`; this checker returned exit status zero for that rejection, so the run
requires the exact `s VERIFIED UNSAT` line in each log.

## Observed checks

`recompute.json` records 160 exact core checks (145 distinct supports), maximum
weighted ranking score `9/19`, 280 variables, 4,161,137 base clauses, and base
SHA-256 `348efbbbbf22f01677e1df2becbffcc1e921afac516431562589ab369d1844cc`.
All 21 independently regenerated leaf CNF hashes and all 21 compressed LRAT
hashes match the pinned `LEAVES.expected.tsv` and on-disk files. The cube
branches are exhaustive because each branch set has its five challengers and
the base contains the corresponding at-least-one clause.

`checks-capped/` is the final complete checker run. Every one of its 21 logs
contains `s VERIFIED UNSAT`; `check-summary-capped.tsv` lists each verdict.
The checker used `prlimit --as=30064771072` (28 GiB hard address-space cap),
`--CML_HEAP_SIZE=26000`, and `--CML_STACK_SIZE=1000`. The live process limit
was confirmed in `/proc/<pid>/limits`. Total checker wall time was 1,008 s;
peak RSS was 26,632,068 KB. The earlier `checks/` run began before the
director's 28 GiB rule, and the complete capped rerun is the final evidence.

## Inference

Together with route A's soundness argument in `CERT.md`, these observations
support the candidate claim for all eight-candidate voter counts. The prior
released bound is m=7; this certificate would extend it to m=8 if a separate
evaluator accepts it.

These are candidate checks. A separate evaluator decides acceptance.
