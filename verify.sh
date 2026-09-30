#!/usr/bin/env bash
# Verify the m = 7 and m = 8, k = 3 Condorcet winning set certificates.
#
#   ./verify.sh            full check: hashes, CNF regeneration, cake_lpr on all
#                          22 proofs (1 for m = 7, 21 for m = 8), cube coverage
#   ./verify.sh --quick    hashes, CNF regeneration, m = 7 proof if present
#
# Needs: bash, python3 with numpy, gcc, git, curl, zstd, xz, sha256sum.
# Full check: cake_lpr peaks near 25.4 GiB RSS with the default heap (runs capped
# at 28 GiB succeeded; use a machine with at least 32 GiB), about 3 GB disk for the leaf CNFs,
# about 25 CPU-minutes, 5.1 GB download. Proofs are read from m7/proofs and
# m8/proofs; a missing proof is downloaded from the GitHub release (PROOF_URL)
# and must match its hash in MANIFEST.sha256.
# Env: CAKE_LPR=/path/to/cake_lpr skips the build; WORK=dir (default ./work);
#      PYTHON=python with numpy (default python3); CAKE_HEAP_MB (default 26000);
#      LEAVES="Lcube-456-3 ..." checks only those m = 8 leaves (coverage then fails).
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$PWD
QUICK=0; [ "${1:-}" = --quick ] && QUICK=1
WORK=${WORK:-$ROOT/work}; mkdir -p "$WORK/m8" "$WORK/checks"
HEAP=${CAKE_HEAP_MB:-26000}
PY=${PYTHON:-python3}
say() { printf '== %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*"; exit 1; }
# MANIFEST.sha256 is the OpenTimestamps-anchored manifest; its own hash is fixed here.
MANIFEST_SHA=ae319c72fe646532c836856be0f86572b8c92d10b84c6de9050815d572c77555
# MANIFEST.post-stamp.sha256 lists the files changed after the stamp (the hardened
# scripts). For those paths it overrides the anchored hash, and verify.sh says so.
POST=$ROOT/MANIFEST.post-stamp.sha256
want() {
  local h
  h=$(awk -v p="$1" '$2 == p { print $1 }' "$POST")
  [ -n "$h" ] || h=$(awk -v p="$1" '$2 == p { print $1 }' "$ROOT/MANIFEST.sha256")
  echo "$h"
}
sha() { sha256sum "$1" | cut -c1-64; }
PROOF_URL=${PROOF_URL:-https://github.com/Aspect5/condorcet-certificates/releases/download/v1}
fetch() {  # fetch PATH: download a missing proof, then check its manifest hash
  [ -f "$1" ] || { mkdir -p "$(dirname "$1")"; curl -fsSL -o "$1.part" "$PROOF_URL/$(basename "$1")" && mv "$1.part" "$1"; }
  [ "$(sha "$1")" = "$(want "$1")" ] || fail "proof hash $1"
}

# The exact checks must run. PYTHONOPTIMIZE is dropped for this script (the checks
# then run in full); an interpreter that still optimizes (PYTHON='python3 -O') is
# refused here, and the generators also refuse to run under -O on their own.
if [ -n "${PYTHONOPTIMIZE:-}" ]; then
  echo "note: PYTHONOPTIMIZE=$PYTHONOPTIMIZE ignored; the exact checks always run"
  unset PYTHONOPTIMIZE
fi
$PY -c 'import sys; sys.exit(sys.flags.optimize)' \
  || fail "PYTHON ($PY) runs with -O; the exact checks would be skipped"

say "1. hashes of the shipped files (MANIFEST.sha256)"
got=$(sha MANIFEST.sha256)
echo "sha256(MANIFEST.sha256)=$got"
[ "$got" = "$MANIFEST_SHA" ] || fail "MANIFEST.sha256 is not the timestamped manifest (want $MANIFEST_SHA)"
echo "sha256(MANIFEST.post-stamp.sha256)=$(sha "$POST")"
# Every manifest entry is accounted for: present and matching, or regenerated
# (CNFs, compared in steps 3-5), or a proof (downloaded and compared in steps 3 and 6).
n_present=0; n_regen=0; n_proof=0
while read -r h p; do
  [ -n "$p" ] || continue
  e=$(want "$p")
  [ "$e" = "$h" ] || echo "superseded after the stamp: $p (anchored ${h:0:12}..., now ${e:0:12}...)"
  if [ -f "$p" ]; then
    [ "$(sha "$p")" = "$e" ] || fail "hash mismatch: $p"
    n_present=$((n_present + 1))
  else
    case $p in
      m7/m7k3.cnf|m8/cnf/*.cnf) n_regen=$((n_regen + 1)) ;;
      m7/proofs/*.lrat.xz|m8/proofs/*.lrat.zst) n_proof=$((n_proof + 1)) ;;
      *) fail "manifest file missing and not regenerated or downloaded: $p" ;;
    esac
  fi
done < MANIFEST.sha256
while read -r h p; do
  [ -n "$p" ] || continue
  grep -q "  $p\$" MANIFEST.sha256 || fail "post-stamp entry not in the manifest: $p"
done < "$POST"
echo "manifest: $n_present present and matching, $n_regen CNFs to regenerate, $n_proof proofs to fetch or check"

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
"$PY" m7/mkcnf.py m7/m7k3.json 7 3 "$WORK/m7k3.cnf" > "$WORK/m7k3.gen.out" || fail "m7 generator"
grep -v '^core ' "$WORK/m7k3.gen.out"
grep -qx 'worst_bound=2/5' "$WORK/m7k3.gen.out" || fail "m7 worst bound is not 2/5"
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
"$PY" m8/cert/gen.py m8/cert/long-160f-all-cores.json --out "$B" > "$WORK/m8-base.gen.out" || fail "m8 generator"
cat "$WORK/m8-base.gen.out"
grep -qx 'worst_bound=9/19' "$WORK/m8-base.gen.out" || fail "m8 worst bound is not 9/19"
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

if [ $QUICK = 1 ]; then say "quick mode: the 21 m = 8 proofs in the manifest were NOT checked"; exit 0; fi

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
[ -z "${LEAVES:-}" ] || fail "LEAVES was set: only some m = 8 proofs were checked"
say "ALL CHECKS PASSED"
