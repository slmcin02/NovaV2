Set-StrictMode -Version Latest
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements-py314.txt
Write-Host "NOVA laptop environment ready."
