#!/usr/bin/env bash
# Level 1 - numeric verification (no model, no raw data).
# Run from the reproduction-package root: bash level1_verify/run_level1.sh
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root" || exit 1
py="${PYTHON:-python}"
fail=0

echo "== 1/4 manuscript + SI invariant check =="
"$py" scripts/check_v6_consistency.py --no-pdf || fail=$((fail+1))

echo "== 2/4 follow-up tables S19-S24 =="
"$py" scripts/verify_followup_tables.py || fail=$((fail+1))

echo "== 3/4 singleton / entropy audit =="
"$py" scripts/singleton_audit.py verify || fail=$((fail+1))

echo "== 4/4 archive checksums =="
"$py" scripts/make_md5sums.py --check || fail=$((fail+1))

if [ "$fail" -gt 0 ]; then
  echo "LEVEL 1 FAILED ($fail checker(s))"
  exit 1
fi
echo "LEVEL 1 PASSED: tables rebuilt from archived metrics; no model was fitted."
