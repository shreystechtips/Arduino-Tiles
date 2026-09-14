$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $projectRoot "build"
$distDir = Join-Path $projectRoot "dist"
$specFile = Join-Path $projectRoot "arduino_tiles.spec"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed. Install uv before building the Windows bundle."
}

Remove-Item -LiteralPath $buildDir, $distDir -Recurse -Force -ErrorAction SilentlyContinue
Push-Location $projectRoot
try {
    & uv run pyinstaller --noconfirm --clean $specFile
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

Write-Host "Windows onedir bundle created under $distDir."
