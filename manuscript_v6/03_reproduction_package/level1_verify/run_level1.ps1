# Level 1 - numeric verification (no model, no raw data)
#
# Verifies explicitly covered table cells and numbering/citation/figure-file map; does not rebuild figures.
# Run from the reproduction-package root:
#   powershell -ExecutionPolicy Bypass -File level1_verify/run_level1.ps1
# Exit code 0 only if every checker passes.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
$failed = 0

Write-Host '== 1/4 manuscript + SI invariant check =='
& $py scripts/check_v6_consistency.py --no-pdf
if ($LASTEXITCODE -ne 0) { $failed++ }

Write-Host '== 2/4 follow-up tables S19-S24 =='
& $py scripts/verify_followup_tables.py
if ($LASTEXITCODE -ne 0) { $failed++ }

Write-Host '== 3/4 singleton / entropy audit =='
& $py scripts/singleton_audit.py verify
if ($LASTEXITCODE -ne 0) { $failed++ }

Write-Host '== 4/4 archive checksums =='
& $py scripts/make_md5sums.py --check
if ($LASTEXITCODE -ne 0) { $failed++ }

if ($failed -gt 0) {
  Write-Host "LEVEL 1 FAILED ($failed checker(s))"
  exit 1
}
Write-Host 'LEVEL 1 PASSED: declared table checks passed on archived metrics; no model was fitted.'
