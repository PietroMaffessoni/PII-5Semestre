$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  $venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
}

if (-not (Test-Path $venvPython)) {
  throw "Nao encontrei o Python do ambiente virtual em .venv ou venv."
}

Set-Location $PSScriptRoot
& $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000
