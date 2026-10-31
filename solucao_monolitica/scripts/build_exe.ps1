# Gera dist\Ensalamento.exe - SOLUCAO PRINCIPAL (modelo monolitico)
# Uso (na raiz do repositorio):  powershell -ExecutionPolicy Bypass -File solucao_monolitica\scripts\build_exe.ps1
$ErrorActionPreference = "Stop"
$solucao = Split-Path -Parent $PSScriptRoot
$raiz = Split-Path -Parent $solucao
Set-Location $solucao

& "$raiz\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name Ensalamento `
    --icon "$solucao\assets\icone.ico" `
    --add-data "$solucao\assets;assets" `
    --hidden-import highspy `
    --collect-binaries highspy `
    --collect-data pulp `
    --exclude-module pytest `
    --exclude-module PyInstaller `
    --distpath "$raiz\dist" --workpath "$raiz\build\monolitica" --specpath "$raiz\build" `
    "$solucao\app.py"

Write-Host "Executavel gerado em dist\Ensalamento.exe"
