[CmdletBinding()]
param(
    [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $SkipAppBuild) {
    & (Join-Path $PSScriptRoot "build.ps1")
}

$appExecutable = Join-Path $repoRoot "dist\Macroblock.exe"
if (-not (Test-Path -LiteralPath $appExecutable)) {
    throw "Application executable missing at $appExecutable. Run scripts\build.ps1 first."
}

$compilerCandidates = @()
if ($env:INNO_SETUP_COMPILER) {
    $compilerCandidates += $env:INNO_SETUP_COMPILER
}
$compilerCandidates += @(
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$innoCompiler = $compilerCandidates |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
    Select-Object -First 1
if (-not $innoCompiler) {
    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php or set INNO_SETUP_COMPILER."
}

$projectFile = Join-Path $repoRoot "pyproject.toml"
$versionLine = Select-String -LiteralPath $projectFile -Pattern '^version\s*=\s*"([^"]+)"$' |
    Select-Object -First 1
if (-not $versionLine) {
    throw "Could not read the application version from $projectFile"
}
$appVersion = $versionLine.Matches[0].Groups[1].Value
$installerScript = Join-Path $repoRoot "installer\Macroblock.iss"

& $innoCompiler "/DMyAppVersion=$appVersion" $installerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed."
}

$installerOutput = Join-Path $repoRoot "dist\installer\Macroblock-Setup-$appVersion.exe"
if (-not (Test-Path -LiteralPath $installerOutput)) {
    throw "Installer compilation finished without producing $installerOutput"
}
Write-Output "Built $installerOutput"
