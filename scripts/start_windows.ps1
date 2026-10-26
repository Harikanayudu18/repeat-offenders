# Start the API (127.0.0.1:8000) and the Vite dev server (http://localhost:5173).
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."
$backend = Start-Process python -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" -PassThru
try {
    Set-Location frontend
    npm install
    npm run dev
} finally {
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id }
}
