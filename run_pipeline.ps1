$env:PYTHONPATH = "."

Write-Host "`n=== [1/4] Automated ingestion (APIs + Reddit posts) ===" -ForegroundColor Cyan
python main.py ingest --track automated
if ($LASTEXITCODE -ne 0) { Write-Host "Stage 1 failed. Aborting." -ForegroundColor Red; exit 1 }

Write-Host "`n=== [2/4] Reddit comment enrichment ===" -ForegroundColor Cyan
python -u extractors\playwright_reddit_comments.py
if ($LASTEXITCODE -ne 0) { Write-Host "Stage 2 failed. Aborting." -ForegroundColor Red; exit 1 }

Write-Host "`n=== [3/4] Parse drop folder ===" -ForegroundColor Cyan
python main.py ingest --track drop_folder
if ($LASTEXITCODE -ne 0) { Write-Host "Stage 3 failed. Aborting." -ForegroundColor Red; exit 1 }

Write-Host "`n=== [4/4] Transform + export ===" -ForegroundColor Cyan
python main.py transform
if ($LASTEXITCODE -ne 0) { Write-Host "Stage 4 failed. Aborting." -ForegroundColor Red; exit 1 }

Write-Host "`n✅ Pipeline complete!" -ForegroundColor Green
