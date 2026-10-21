# Rebuild the two submission PDFs and run the acceptance checks.
# Usage: right-click -> "Run with PowerShell", or from any directory:
#   powershell -ExecutionPolicy Bypass -File "C:\...\03_投稿专用包_v6压缩\rebuild_pdfs.ps1"
# Requires a working local Microsoft Edge (headless print-to-pdf) and Python 3.9+.

$ErrorActionPreference = "Stop"
$pkg = Join-Path $PSScriptRoot "03_reproduction_package"
Set-Location $pkg

Write-Host "== package: $pkg" -ForegroundColor Cyan

Write-Host "`n[1/4] rebuilding Manuscript_v6.pdf ..." -ForegroundColor Cyan
python scripts\build_pdf_v6.py

Write-Host "`n[2/4] rebuilding SI_v6.pdf ..." -ForegroundColor Cyan
python scripts\build_pdf_v6.py --si

Write-Host "`n[3/4] consistency check (expect: all 555 checks passed) ..." -ForegroundColor Cyan
python scripts\check_v6_consistency.py
$checkExit = $LASTEXITCODE

Write-Host "`n[4/4] archive manifest ..." -ForegroundColor Cyan
python scripts\make_md5sums.py --check

if ($checkExit -ne 0) {
    Write-Host "`nConsistency check reported a problem - read the FAIL lines above." -ForegroundColor Yellow
} else {
    Write-Host "`nDone: PDFs rebuilt and all checks passed." -ForegroundColor Green
}
Write-Host "Press Enter to close."
Read-Host | Out-Null
