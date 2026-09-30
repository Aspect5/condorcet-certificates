#!/usr/bin/env bash
# Regression tests for referee issues 1-3 (2026-09-30).
#   tests/test_hardening.sh [REPO_DIR]     (default: this checkout)
# Env: PYTHON=python3 with numpy (for the m = 8 generator test).
# Each test plants a defect in a scratch copy and requires a nonzero exit with
# the expected message. verify.sh tests stop after TMO seconds: a verifier that
# has not rejected the plant by then fails the test.
set -uo pipefail
REPO=$(cd "${1:-$(dirname "$0")/..}" && pwd)
PY=${PYTHON:-python3}
TMO=${TMO:-90}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; failn=0
ok() { echo "PASS $1"; pass=$((pass + 1)); }
bad() { echo "FAIL $1: $2"; failn=$((failn + 1)); }
copy() { rm -rf "$T/r"; mkdir -p "$T/r"; (cd "$REPO" && tar --exclude=.git --exclude=work --exclude=proofs -cf - .) | tar -C "$T/r" -xf -; }
plant_m7() {  # $1 = weights JSON for the first core of m7k3.json
  "$PY" - "$1" "$2" "$3" <<'P'
import json, sys
d = json.load(open(sys.argv[2])); d['dual_leaves'][0]['weights'] = json.loads(sys.argv[1])
json.dump(d, open(sys.argv[3], 'w'))
P
}
expect_reject() {  # name, expected-message, command...
  local name=$1 msg=$2; shift 2
  out=$("$@" 2>&1); rc=$?
  if [ $rc -ne 0 ] && grep -qF -- "$msg" <<<"$out"; then ok "$name"
  else bad "$name" "exit $rc, output tail: $(tail -2 <<<"$out" | tr '\n' ' ')"; fi
}

# Issue 1: planted non-core (bound 9/10) under PYTHONOPTIMIZE=1 must be rejected.
plant_m7 '[[4,"9/10"],[20,"1/20"],[60,"1/20"]]' "$REPO/m7/m7k3.json" "$T/bad.json"
expect_reject "1a m7 non-core, PYTHONOPTIMIZE=1" "FAIL" \
  env PYTHONOPTIMIZE=1 "$PY" "$REPO/m7/mkcnf.py" "$T/bad.json" 7 3 "$T/bad.cnf"
expect_reject "1b m7 non-core, python -O" "FAIL" \
  "$PY" -O "$REPO/m7/mkcnf.py" "$T/bad.json" 7 3 "$T/bad.cnf"
expect_reject "1c m7 non-core, no -O" "not a core: bound 9/10" \
  env -u PYTHONOPTIMIZE "$PY" "$REPO/m7/mkcnf.py" "$T/bad.json" 7 3 "$T/bad.cnf"
plant_m7 '[[4,"1/2"],[20,"1/2"],[60,"0"]]' "$REPO/m7/m7k3.json" "$T/zero.json"
expect_reject "1d m7 zero weight, no -O" "nonpositive weight" \
  env -u PYTHONOPTIMIZE "$PY" "$REPO/m7/mkcnf.py" "$T/zero.json" 7 3 "$T/z.cnf"
plant_m7 '[[4,"1/3"],[20,"1/3"],[60,"1/2"]]' "$REPO/m7/m7k3.json" "$T/sum.json"
expect_reject "1e m7 weights sum 7/6, no -O" "weights sum to 7/6" \
  env -u PYTHONOPTIMIZE "$PY" "$REPO/m7/mkcnf.py" "$T/sum.json" 7 3 "$T/s.cnf"
# m = 8 generator: a single planted non-core (weight 9/10 on one event).
echo '[[[0,"9/10"],[1,"1/20"],[2,"1/20"]]]' > "$T/bad8.json"
expect_reject "1f m8 non-core, PYTHONOPTIMIZE=1" "FAIL" \
  env PYTHONOPTIMIZE=1 "$PY" "$REPO/m8/cert/gen.py" "$T/bad8.json" --out "$T/bad8.cnf"
expect_reject "1g m8 non-core, no -O" "not a core" \
  env -u PYTHONOPTIMIZE "$PY" "$REPO/m8/cert/gen.py" "$T/bad8.json" --out "$T/bad8.cnf"
# Genuine m = 7 cores: machine-readable worst_bound line.
out=$(env -u PYTHONOPTIMIZE "$PY" "$REPO/m7/mkcnf.py" "$REPO/m7/m7k3.json" 7 3 "$T/good.cnf" 2>&1)
grep -qx 'worst_bound=2/5' <<<"$out" && ok "1h m7 prints worst_bound=2/5" || bad "1h m7 prints worst_bound=2/5" "line absent"
# verify.sh refuses an optimizing interpreter before doing any work.
copy
expect_reject "1i verify.sh refuses PYTHON='python -O'" "runs with -O" \
  env -u PYTHONOPTIMIZE PYTHON="$PY -O" WORK="$T/w1" timeout "$TMO" "$T/r/verify.sh" --quick
# The referee's end-to-end plant: non-core m7k3.json plus its manifest line, under
# PYTHONOPTIMIZE=1. The original verify.sh passes it; the fixed one must reject it.
cp "$T/bad.json" "$T/r/m7/m7k3.json"
h=$(sha256sum "$T/r/m7/m7k3.json" | cut -c1-64)
sed -i "s|^[0-9a-f]\{64\}  m7/m7k3.json$|$h  m7/m7k3.json|" "$T/r/MANIFEST.sha256"
expect_reject "1k verify.sh rejects planted non-core under PYTHONOPTIMIZE=1" "FAIL" \
  env PYTHONOPTIMIZE=1 PYTHON="$PY" WORK="$T/w1k" timeout "$TMO" "$T/r/verify.sh" --quick
grep -q "grep -qx 'worst_bound=2/5'" "$REPO/verify.sh" && grep -q "grep -qx 'worst_bound=9/19'" "$REPO/verify.sh" \
  && ok "1j verify.sh requires worst_bound=2/5 and 9/19" || bad "1j verify.sh requires worst_bound=2/5 and 9/19" "no such check"

# Issue 2: a consistently edited manifest (file and its line) must be rejected.
copy
echo "planted" >> "$T/r/m7/recompute/RESULTS.md"
h=$(sha256sum "$T/r/m7/recompute/RESULTS.md" | cut -c1-64)
sed -i "s|^[0-9a-f]\{64\}  m7/recompute/RESULTS.md$|$h  m7/recompute/RESULTS.md|" "$T/r/MANIFEST.sha256"
expect_reject "2a edited manifest rejected" "not the timestamped manifest" \
  env -u PYTHONOPTIMIZE PYTHON="$PY" WORK="$T/w2" timeout "$TMO" "$T/r/verify.sh" --quick
# A manifest file deleted from the checkout must be flagged, not skipped.
copy
rm "$T/r/m8/cert/control.py"
expect_reject "2b missing manifest file flagged" "manifest file missing and not regenerated or downloaded: m8/cert/control.py" \
  env -u PYTHONOPTIMIZE PYTHON="$PY" WORK="$T/w3" timeout "$TMO" "$T/r/verify.sh" --quick
out=$(env -u PYTHONOPTIMIZE PYTHON="$PY" WORK="$T/w4" timeout 20 bash -c "cd '$REPO' && ./verify.sh --quick" 2>&1)
grep -q '^sha256(MANIFEST.sha256)=ae319c72fe646532c836856be0f86572b8c92d10b84c6de9050815d572c77555$' <<<"$out" \
  && ok "2c verify.sh prints the anchored manifest hash" || bad "2c verify.sh prints the anchored manifest hash" "line absent in first 20 s"

# Issue 3: default heap 26000 and the README states the 28 GiB cap.
grep -q 'HEAP=${CAKE_HEAP_MB:-26000}' "$REPO/verify.sh" && ok "3a default CAKE_HEAP_MB=26000" || bad "3a default CAKE_HEAP_MB=26000" "$(grep -o 'HEAP=.*' "$REPO/verify.sh")"
grep -q '28 GiB' "$REPO/README.md" && grep -q 'CAKE_HEAP_MB=26000' "$REPO/README.md" \
  && ok "3b README states 28 GiB cap and heap 26000" || bad "3b README states 28 GiB cap and heap 26000" "not stated"

echo "tests: $pass passed, $failn failed"
[ $failn -eq 0 ]
