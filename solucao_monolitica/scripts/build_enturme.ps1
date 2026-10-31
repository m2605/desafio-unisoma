# Gera dist\Enturme.exe - interface visual Enturme (modelo monolitico)
# Uso (na raiz do repositorio):  powershell -ExecutionPolicy Bypass -File solucao_monolitica\scripts\build_enturme.ps1
$ErrorActionPreference = "Stop"
$solucao = Split-Path -Parent $PSScriptRoot
$raiz = Split-Path -Parent $solucao
Set-Location $solucao

& "$raiz\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name Enturme `
    --icon "$solucao\assets\enturme.ico" `
    --add-data "$solucao\assets;assets" `
    --paths "$solucao" `
    --hidden-import highspy `
    --collect-binaries highspy `
    --collect-data pulp `
    --collect-all tkinterdnd2 `
    --exclude-module pytest `
    --exclude-module PyInstaller `
    --distpath "$raiz\dist" --workpath "$raiz\build\enturme" --specpath "$raiz\build" `
    "$solucao\app_enturme.py"

Write-Host "Executavel gerado em dist\Enturme.exe"
