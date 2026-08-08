$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python not found. Create .venv as documented or place Python on PATH."
    }
    $python = $pythonCommand.Source
}

& $python (Join-Path $repoRoot "tools\generate_icon.py")
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed." }

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Macroblock `
    --icon (Join-Path $repoRoot "assets\icons\macroblock.ico") `
    --add-data "$(Join-Path $repoRoot 'assets\icons\macroblock.ico');assets\icons" `
    --paths (Join-Path $repoRoot "src") `
    --distpath (Join-Path $repoRoot "dist") `
    --workpath (Join-Path $repoRoot "build\pyinstaller") `
    --specpath (Join-Path $repoRoot "build") `
    (Join-Path $repoRoot "src\macroblock\main.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$output = Join-Path $repoRoot "dist\Macroblock.exe"
if (-not (Test-Path -LiteralPath $output)) {
    throw "Build completed without producing $output"
}
Write-Output "Built $output"
