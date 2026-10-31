# Gera dist\Ensalamento.exe (executavel unico, sem precisar instalar Python)
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name Ensalamento `
    --icon assets\icone.ico `
    --add-data "assets;assets" `
    --hidden-import highspy `
    --collect-binaries highspy `
    --collect-data pulp `
    --exclude-module pytest `
    --exclude-module PyInstaller `
    app.py

Write-Host "Executavel gerado em dist\Ensalamento.exe"
