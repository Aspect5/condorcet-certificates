
## 2026-09-30: verifier hardening

An external referee found that the certificate generators' soundness checks were bare Python `assert`s. Under `PYTHONOPTIMIZE=1` they were skipped, and `verify.sh` could print `ALL CHECKS PASSED` on a planted formula whose cores are not cores. The certificates and proofs themselves are unchanged. The fixes:
- Every soundness check is now explicit and exits nonzero. The generators refuse to run under `-O` and print `worst_bound=...`; `verify.sh` requires exactly `worst_bound=2/5` (m=7) and `worst_bound=9/19` (m=8), and refuses an optimizing `PYTHON`.
- `verify.sh` prints and checks the manifest's own sha256 (`ae319c72...7555`), and requires every manifest entry to be present, regenerated or checked (no `--ignore-missing`). The four hardened scripts' new hashes are in `MANIFEST.post-stamp.sha256`; the timestamped manifest is unchanged.
- The default `CAKE_HEAP_MB` is 26000; the README states the 28 GiB memory cap.
- `tests/test_hardening.sh`: 16 checks; all fail on the previous release (1982b4f) and all pass here.
