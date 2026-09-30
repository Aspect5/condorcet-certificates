#!/usr/bin/env bash
# Verify the m = 7 and m = 8, k = 3 Condorcet winning set certificates.
#
#   ./verify.sh            full check: hashes, CNF regeneration, cake_lpr on all
#                          22 proofs (1 for m = 7, 21 for m = 8), cube coverage
#   ./verify.sh --quick    hashes, CNF regeneration, m = 7 proof if present
#
# Needs: bash, python3 with numpy, gcc, git, curl, zstd, xz, sha256sum.
# Full check: about 30 GB RAM for cake_lpr, about 3 GB disk for the leaf CNFs,
# about 25 CPU-minutes, 5.1 GB download. Proofs are read from m7/proofs and
# m8/proofs; a missing proof is downloaded from the GitHub release (PROOF_URL)
# and must match its hash in MANIFEST.sha256.
# Env: CAKE_LPR=/path/to/cake_lpr skips the build; WORK=dir (default ./work);
#      PYTHON=python with numpy (default python3); CAKE_HEAP_MB (default 30000);
#      LEAVES="Lcube-456-3 ..." checks only those m = 8 leaves (coverage then fails).
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$PWD
QUICK=0; [ "${1:-}" = --quick ] && QUICK=1
WORK=${WORK:-$ROOT/work}; mkdir -p "$WORK/m8" "$WORK/checks"
HEAP=${CAKE_HEAP_MB:-30000}
PY=${PYTHON:-python3}
say() { printf '== %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*"; exit 1; }
want() { awk -v p="$1" '$2 == p { print $1 }' "$ROOT/MANIFEST.sha256"; }
sha() { sha256sum "$1" | cut -c1-64; }
PROOF_URL=${PROOF_URL:-https://github.com/Aspect5/condorcet-certificates/releases/download/v1}
fetch() {  # fetch PATH: download a missing proof, then check its manifest hash
  [ -f "$1" ] || { mkdir -p "$(dirname "$1")"; curl -fsSL -o "$1.part" "$PROOF_URL/$(basename "$1")" && mv "$1.part" "$1"; }
  [ "$(sha "$1")" = "$(want "$1")" ] || fail "proof hash $1"
}

say "1. hashes of the shipped files (MANIFEST.sha256)"
sha256sum --quiet --ignore-missing -c MANIFEST.sha256 || fail "manifest mismatch"

say "2. cake_lpr (formally verified LRAT checker, CakeML)"
if [ -z "${CAKE_LPR:-}" ]; then
  src=$WORK/cake_lpr_src
  if [ ! -d "$src" ]; then
    git clone -q https://github.com/tanyongkiam/cake_lpr.git "$src"
  fi
  git -C "$src" checkout -q a36874a8b750b43fe4b385b8ddbf5b033e46a3fa
  [ "$(sha "$src/cake_lpr.S")" = 2f3af32d55083839b3fa0e693afd817679c0b8944bef41def05a8b0ec72b7d4a ] \
    || fail "cake_lpr.S hash differs from the pinned commit"
  (cd "$src" && gcc -O2 basis_ffi.c cake_lpr.S -o cake_lpr -std=c99)
  CAKE_LPR=$src/cake_lpr
fi
# cake_lpr exits 0 even when it rejects a proof; only the exact line counts.
cake() { "$CAKE_LPR" --CML_HEAP_SIZE="$HEAP" --CML_STACK_SIZE=4000 "$1" "$2"; }

say "3. m = 7: regenerate the CNF from the Farkas cores (exact rationals, all 5,040 rankings)"
"$PY" m7/mkcnf.py m7/m7k3.json 7 3 "$WORK/m7k3.cnf" | tail -2
[ "$(sha "$WORK/m7k3.cnf")" = "$(want m7/m7k3.cnf)" ] || fail "m7 CNF hash"
if [ $QUICK = 0 ] || [ -f m7/proofs/m7k3.lrat.xz ]; then
  fetch m7/proofs/m7k3.lrat.xz
  fifo=$WORK/m7.fifo; rm -f "$fifo"; mkfifo "$fifo"
  xz -dc < m7/proofs/m7k3.lrat.xz > "$fifo" &
  cake "$WORK/m7k3.cnf" "$fifo" > "$WORK/checks/m7k3.check" 2>&1 || true
  wait; rm -f "$fifo"
  grep -qx 's VERIFIED UNSAT' "$WORK/checks/m7k3.check" || fail "m7 proof not verified"
  echo "m7k3: s VERIFIED UNSAT"
else
  echo "quick mode, m7/proofs/m7k3.lrat.xz absent: m = 7 proof not checked"
fi

say "4. m = 8: regenerate the base CNF (exact check of every core on all 40,320 rankings)"
B=$WORK/m8/A145-none.cnf
"$PY" m8/cert/gen.py m8/cert/long-160f-all-cores.json --out "$B"
[ "$(sha "$B")" = "$(want m8/cnf/A145-none.cnf)" ] || fail "m8 base CNF hash"

say "5. m = 8: the 21 cube leaves"
(
  cd "$WORK/m8"
  "$PY" "$ROOT/m8/cert/mkcube.py" A145-none.cnf A145-none-c456 '4,5,6:*' > /dev/null
  mv A145-none-c456-456-3.cnf A145-none-c456-3.cnf
  rm -f A145-none-c456-456-*.cnf
  for c in 0 1 2; do "$PY" "$ROOT/m8/cert/mkcube.py" A145-none.cnf A145-none-c456-$c "4,5,6:$c" '5,6,7:*' > /dev/null; done
  "$PY" "$ROOT/m8/cert/mkcube.py" A145-none.cnf A145-none-c456-7 '4,5,6:7' '4,5,7:*' > /dev/null
)
leafcnf() { case $1 in Lcube-456-3) echo A145-none-c456-3.cnf ;; *) echo "A145-none-${1#L}.cnf" ;; esac; }
ALL=$(tail -n +2 m8/cert/LEAVES.tsv | cut -f1)
for t in $ALL; do
  f=$(leafcnf "$t")
  [ "$(sha "$WORK/m8/$f")" = "$(want "m8/cnf/$f")" ] || fail "leaf CNF hash $f"
done
echo "21/21 leaf CNF hashes match"

if [ $QUICK = 1 ]; then say "quick mode: m = 8 proofs not checked"; exit 0; fi

say "6. m = 8: cake_lpr on each leaf proof"
for t in ${LEAVES:-$ALL}; do
  f=$(leafcnf "$t"); p=m8/proofs/$t.lrat.zst
  fetch "$p"
  fifo=$WORK/$t.fifo; rm -f "$fifo"; mkfifo "$fifo"
  zstd -dcq < "$p" > "$fifo" &
  cake "$WORK/m8/$f" "$fifo" > "$WORK/checks/$t.check" 2>&1 || true
  wait; rm -f "$fifo"
  printf 'cnf_sha256=%s\n' "$(sha "$WORK/m8/$f")" >> "$WORK/checks/$t.check"
  grep -qx 's VERIFIED UNSAT' "$WORK/checks/$t.check" || fail "$t not verified"
  echo "$t: s VERIFIED UNSAT"
done

say "7. m = 8: leaves extend the base by unit cubes only, and the cubes cover every case"
"$PY" m8/cert/cover.py "$B" "$WORK/checks" $(for t in $ALL; do echo "$WORK/m8/$(leafcnf "$t")"; done) | tee "$WORK/cover.out"
tail -1 "$WORK/cover.out" | grep -qx 'COVERED | all leaves verified' || fail "coverage"
say "ALL CHECKS PASSED"
