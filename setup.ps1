# Run from the accesslens folder in PowerShell:  .\setup.ps1
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python -m pytest -q
Write-Host "`nSetup done. Start server:  uvicorn app.main:app   (no --reload on Windows)"
