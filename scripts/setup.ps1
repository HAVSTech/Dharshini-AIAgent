$ErrorActionPreference = "Stop"
Write-Host "Setting up Dharshini AI Agent..."
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env. Add your GEMINI_API_KEY." }
Write-Host "Setup complete."
